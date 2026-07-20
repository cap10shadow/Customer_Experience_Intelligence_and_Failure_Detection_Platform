import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.services.anomaly_service.app.models.incident import Incident
from backend.services.anomaly_service.app.repositories.anomaly_repository import AnomalyRepository
from backend.services.anomaly_service.app.repositories.incident_repository import IncidentRepository
from backend.services.anomaly_service.app.schemas.anomalies import ActiveAnomalyResponse
from backend.services.anomaly_service.app.schemas.incidents import IncidentResponse, IncidentRunItem, IncidentRunResult
from backend.services.anomaly_service.app.services.explanation import build_resolved_reason, build_summary
from backend.services.anomaly_service.app.services.incident_builder import (
    aggregate_severity,
    build_title,
    generate_incident_key,
)
from backend.services.anomaly_service.app.services.rules import (
    category_rule,
    region_rule,
    severity_rule,
    supporting_signal_rule,
    timing_rule,
)
from backend.services.anomaly_service.app.services.scoring import (
    DEFAULT_TIME_WINDOW_MINUTES,
    MIN_CONFIDENCE_TO_CORRELATE,
    ConfidenceScore,
    combine,
)
from backend.shared.constants.enums.anomaly import AnomalyStatus
from backend.shared.constants.enums.incident import IncidentStatus


class CorrelationEngine:
    """
    Incident Correlation Engine

    Ownership:
    Owned by the Anomaly Service.

    Operational Purpose:
    Groups related active anomalies into Incidents using deterministic
    rules only (temporal proximity, shared region/category/severity,
    supporting operational signals). Does not perform Root Cause Analysis —
    that is a future phase; this engine only determines *that* a set of
    anomalies are likely manifestations of the same problem, not *why*.

    Philosophy:
    - Deterministic only: candidate clusters are formed by a simple time-gap
      sweep (not statistical clustering), then scored by five independent,
      centrally-configured rules. No ML, no embeddings.
    - Anomalies are immutable evidence: this engine only reads
      `active_anomalies` (via AnomalyRepository) and never writes to it or
      to `anomaly_history`. Incident persistence — including relationships
      via `incident_anomalies` — is entirely separate.
    - Sequential by construction: all repository calls share one
      AsyncSession, so everything is awaited one at a time rather than via
      asyncio.gather.
    - Idempotent by construction: re-running with no new anomalies re-uses
      existing incidents and links, producing no new incidents, no
      duplicate links, and no history churn.
    """

    def __init__(self, incident_repository: IncidentRepository, anomaly_repository: AnomalyRepository) -> None:
        self.incident_repository = incident_repository
        self.anomaly_repository = anomaly_repository

    async def run(self, window_minutes: int = DEFAULT_TIME_WINDOW_MINUTES) -> IncidentRunResult:
        run_at = datetime.now(timezone.utc)
        active_anomalies = await self.anomaly_repository.list_active()

        created: List[IncidentRunItem] = []
        updated: List[IncidentRunItem] = []

        for cluster in _cluster_by_time(active_anomalies, window_minutes):
            if len(cluster) < 2:
                # A single anomaly has nothing to correlate with; it stays
                # unlinked until a future run finds it a companion.
                continue

            confidence = _score_cluster(cluster, window_minutes)
            if confidence.score < MIN_CONFIDENCE_TO_CORRELATE:
                continue

            existing = await self._find_existing_incident(cluster)
            if existing is None:
                created.append(await self._create_incident(cluster, confidence, run_at))
            else:
                item = await self._update_incident(existing, cluster, confidence, run_at)
                if item is not None:
                    updated.append(item)

        resolved = await self._resolve_completed_incidents(run_at)

        return IncidentRunResult(run_at=run_at, created=created, updated=updated, resolved=resolved)

    async def get_active(self) -> List[IncidentResponse]:
        incidents = await self.incident_repository.list_open()
        return [IncidentResponse.model_validate(i) for i in incidents]

    async def get_by_id(self, incident_id: uuid.UUID) -> Optional[IncidentResponse]:
        incident = await self.incident_repository.get_by_id(incident_id)
        return IncidentResponse.model_validate(incident) if incident else None

    async def get_anomalies_for_incident(self, incident_id: uuid.UUID) -> Optional[List[ActiveAnomalyResponse]]:
        """Returns None if the incident itself doesn't exist, else its linked anomalies (possibly empty)."""
        incident = await self.incident_repository.get_by_id(incident_id)
        if incident is None:
            return None
        anomalies = await self.incident_repository.list_linked_anomalies(incident_id)
        return [ActiveAnomalyResponse.model_validate(a) for a in anomalies]

    # ------------------------------------------------------------------
    # Reconciliation transitions
    # ------------------------------------------------------------------

    async def _find_existing_incident(self, cluster: List[ActiveAnomaly]) -> Optional[Incident]:
        """
        Reuses an existing OPEN incident if any anomaly in this cluster is
        already linked to one — the cluster is sorted by first_detected_at,
        so this deterministically prefers the incident tied to the
        earliest-detected anomaly when more than one could apply.
        """
        for anomaly in cluster:
            incident = await self.incident_repository.get_open_incident_for_anomaly(anomaly.id)
            if incident is not None:
                return incident
        return None

    async def _create_incident(
        self, cluster: List[ActiveAnomaly], confidence: ConfidenceScore, run_at: datetime
    ) -> IncidentRunItem:
        incident = Incident(
            incident_key=generate_incident_key(),
            title=build_title(cluster),
            severity=aggregate_severity(cluster),
            status=IncidentStatus.OPEN,
            confidence_score=confidence.score,
            summary=build_summary(cluster, confidence),
            started_at=run_at,
            last_updated_at=run_at,
            resolved_at=None,
        )
        created = await self.incident_repository.create_incident(incident)
        for anomaly in cluster:
            await self.incident_repository.link_anomaly(created.id, anomaly.id, run_at)

        return IncidentRunItem(
            incident=IncidentResponse.model_validate(created),
            linked_anomaly_count=len(cluster),
            reason=f"New incident correlated from {len(cluster)} anomalies.",
        )

    async def _update_incident(
        self, incident: Incident, cluster: List[ActiveAnomaly], confidence: ConfidenceScore, run_at: datetime
    ) -> Optional[IncidentRunItem]:
        newly_linked = []
        for anomaly in cluster:
            if not await self.incident_repository.is_anomaly_linked(incident.id, anomaly.id):
                await self.incident_repository.link_anomaly(incident.id, anomaly.id, run_at)
                newly_linked.append(anomaly)

        all_linked = await self.incident_repository.list_linked_anomalies(incident.id)
        new_severity = aggregate_severity(all_linked)

        changed = bool(newly_linked) or confidence.score != incident.confidence_score or new_severity != incident.severity
        if not changed:
            # Routine re-confirmation: nothing meaningful changed, so the
            # incident row is left untouched (no update churn).
            return None

        incident.confidence_score = confidence.score
        incident.severity = new_severity
        incident.title = build_title(all_linked)
        incident.summary = build_summary(all_linked, confidence)
        incident.last_updated_at = run_at
        await self.incident_repository.save(incident)

        reason = (
            f"{len(newly_linked)} new anomaly(ies) linked."
            if newly_linked
            else "Confidence or severity recalculated."
        )
        return IncidentRunItem(
            incident=IncidentResponse.model_validate(incident),
            linked_anomaly_count=len(all_linked),
            reason=reason,
        )

    async def _resolve_completed_incidents(self, run_at: datetime) -> List[IncidentRunItem]:
        resolved: List[IncidentRunItem] = []
        for incident in await self.incident_repository.list_open():
            linked = await self.incident_repository.list_linked_anomalies(incident.id)
            if linked and all(a.status == AnomalyStatus.RESOLVED for a in linked):
                incident.status = IncidentStatus.RESOLVED
                incident.resolved_at = run_at
                incident.last_updated_at = run_at
                await self.incident_repository.save(incident)
                resolved.append(
                    IncidentRunItem(
                        incident=IncidentResponse.model_validate(incident),
                        linked_anomaly_count=len(linked),
                        reason=build_resolved_reason(),
                    )
                )
        return resolved


def _cluster_by_time(anomalies: List[ActiveAnomaly], window_minutes: int) -> List[List[ActiveAnomaly]]:
    """
    Deterministic time-gap sweep: sorts anomalies by first_detected_at and
    starts a new cluster whenever the gap to the previous anomaly exceeds
    `window_minutes`. Not statistical clustering — a single fixed threshold
    applied in one linear pass.
    """
    ordered = sorted(anomalies, key=lambda a: a.first_detected_at)
    clusters: List[List[ActiveAnomaly]] = []
    current: List[ActiveAnomaly] = []

    for anomaly in ordered:
        if current and (anomaly.first_detected_at - current[-1].first_detected_at) > timedelta(minutes=window_minutes):
            clusters.append(current)
            current = []
        current.append(anomaly)

    if current:
        clusters.append(current)
    return clusters


def _score_cluster(cluster: List[ActiveAnomaly], window_minutes: int) -> ConfidenceScore:
    rule_results = [
        timing_rule.evaluate(cluster, window_minutes),
        region_rule.evaluate(cluster),
        category_rule.evaluate(cluster),
        severity_rule.evaluate(cluster),
        supporting_signal_rule.evaluate(cluster),
    ]
    return combine(rule_results)
