import uuid
from datetime import datetime, timezone
from typing import List, Optional, Set

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly, AnomalyHistory
from backend.services.anomaly_service.app.repositories.anomaly_repository import AnomalyRepository
from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.schemas.anomalies import (
    ActiveAnomalyResponse,
    AnomalyRunItem,
    AnomalyRunResult,
)
from backend.services.anomaly_service.app.services.detectors.category_detector import CategoryDetector
from backend.services.anomaly_service.app.services.detectors.region_detector import RegionDetector
from backend.services.anomaly_service.app.services.detectors.sentiment_detector import SentimentDetector
from backend.services.anomaly_service.app.services.detectors.urgency_detector import UrgencyDetector
from backend.services.anomaly_service.app.services.detectors.volume_detector import VolumeDetector
from backend.services.anomaly_service.app.services.explainability import (
    build_detected_reason,
    build_resolved_reason,
    build_updated_reason,
)
from backend.services.anomaly_service.app.services.fingerprint import AnomalyCandidate, compute_fingerprint
from backend.services.anomaly_service.app.utils.time_window import resolve_comparison_windows
from backend.shared.constants.enums.anomaly import AnomalyEventType, AnomalyStatus, AnomalySeverity


class AnomalyEngine:
    """
    Anomaly Detection Engine

    Ownership:
    Owned by the Anomaly Service.

    Operational Purpose:
    Orchestrates the deterministic detectors, reconciles their findings
    against `active_anomalies` by fingerprint, and records lifecycle
    transitions in `anomaly_history` only when something meaningful changed.

    Philosophy:
    - Deterministic only: every detector compares a current window against
      the previous equivalent window using fixed percentage-change
      thresholds. No forecasting, no moving averages, no ML.
    - Sequential by construction: detectors and repository calls share one
      AsyncSession, so everything is awaited one at a time rather than via
      asyncio.gather (concurrent use of a single AsyncSession is unsupported).
    - History is append-only and written only on DETECTED, a severity
      change (UPDATED), or RESOLVED — never on routine re-confirmation of an
      unchanged anomaly.
    """

    def __init__(self, repository: AnomalyRepository, trend_repository: TrendRepository) -> None:
        self.repository = repository
        self.detectors = [
            VolumeDetector(trend_repository),
            CategoryDetector(trend_repository),
            RegionDetector(trend_repository),
            UrgencyDetector(trend_repository),
            SentimentDetector(trend_repository),
        ]

    async def run(self, days: int) -> AnomalyRunResult:
        current_window, previous_window = resolve_comparison_windows(days)
        run_at = datetime.now(timezone.utc)

        candidates: List[AnomalyCandidate] = []
        for detector in self.detectors:
            candidates.extend(await detector.detect(current_window, previous_window))

        detected: List[AnomalyRunItem] = []
        updated: List[AnomalyRunItem] = []
        resolved: List[AnomalyRunItem] = []
        seen_fingerprints: Set[str] = set()

        for candidate in candidates:
            fingerprint = compute_fingerprint(candidate.type, candidate.entity_type, candidate.entity_value)
            seen_fingerprints.add(fingerprint)

            existing = await self.repository.get_active_by_fingerprint(fingerprint)
            if existing is None:
                detected.append(await self._create_new(fingerprint, candidate, run_at))
            elif existing.status == AnomalyStatus.RESOLVED:
                detected.append(await self._reactivate(existing, candidate, run_at))
            else:
                item = await self._update_existing(existing, candidate, run_at)
                if item is not None:
                    updated.append(item)

        for anomaly in await self.repository.list_active():
            if anomaly.fingerprint not in seen_fingerprints:
                resolved.append(await self._resolve(anomaly, run_at))

        return AnomalyRunResult(
            run_at=run_at,
            period=current_window.label,
            detected=detected,
            updated=updated,
            resolved=resolved,
        )

    async def get_active(self) -> List[ActiveAnomalyResponse]:
        anomalies = await self.repository.list_active()
        return [ActiveAnomalyResponse.model_validate(a) for a in anomalies]

    async def get_by_id(self, anomaly_id: uuid.UUID) -> Optional[ActiveAnomalyResponse]:
        anomaly = await self.repository.get_by_id(anomaly_id)
        return ActiveAnomalyResponse.model_validate(anomaly) if anomaly else None

    async def get_latest(self) -> AnomalyRunResult:
        """
        Reconstructs the outcome of the most recent `run()` from persisted
        state, without re-running detection: every history event whose
        `event_timestamp` matches the latest run's timestamp.
        """
        latest_ts = await self.repository.get_latest_run_timestamp()
        if latest_ts is None:
            return AnomalyRunResult()

        detected: List[AnomalyRunItem] = []
        updated: List[AnomalyRunItem] = []
        resolved: List[AnomalyRunItem] = []

        for event in await self.repository.list_history_at(latest_ts):
            anomaly = await self.repository.get_by_id(event.active_anomaly_id)
            if anomaly is None:
                continue
            item = AnomalyRunItem(anomaly=ActiveAnomalyResponse.model_validate(anomaly), reason=event.reason)
            if event.event_type == AnomalyEventType.DETECTED:
                detected.append(item)
            elif event.event_type == AnomalyEventType.UPDATED:
                updated.append(item)
            elif event.event_type == AnomalyEventType.RESOLVED:
                resolved.append(item)

        return AnomalyRunResult(run_at=latest_ts, detected=detected, updated=updated, resolved=resolved)

    # ------------------------------------------------------------------
    # Reconciliation transitions
    # ------------------------------------------------------------------

    async def _create_new(self, fingerprint: str, candidate: AnomalyCandidate, run_at: datetime) -> AnomalyRunItem:
        anomaly = ActiveAnomaly(
            fingerprint=fingerprint,
            type=candidate.type,
            severity=candidate.severity,
            entity_type=candidate.entity_type,
            entity_value=candidate.entity_value,
            baseline_value=candidate.baseline_value,
            current_value=candidate.current_value,
            percentage_change=candidate.percentage_change,
            triggered_rule=candidate.triggered_rule,
            explanation=candidate.explanation,
            first_detected_at=run_at,
            last_seen_at=run_at,
            status=AnomalyStatus.ACTIVE,
        )
        created = await self.repository.create_active(anomaly)

        reason = build_detected_reason(candidate.explanation)
        await self.repository.add_history_event(
            AnomalyHistory(
                active_anomaly_id=created.id,
                event_type=AnomalyEventType.DETECTED,
                old_severity=None,
                new_severity=candidate.severity,
                reason=reason,
                metrics_snapshot=_snapshot(candidate),
                event_timestamp=run_at,
            )
        )
        return AnomalyRunItem(anomaly=ActiveAnomalyResponse.model_validate(created), reason=reason)

    async def _reactivate(self, existing: ActiveAnomaly, candidate: AnomalyCandidate, run_at: datetime) -> AnomalyRunItem:
        """A fingerprint that was RESOLVED is detected again: reopen the same row
        (the fingerprint is unique, so this updates in place rather than inserting).
        `first_detected_at` is left untouched — it always reflects the very first
        detection of this fingerprint, not this re-detection."""
        _apply_candidate(existing, candidate)
        existing.last_seen_at = run_at
        existing.status = AnomalyStatus.ACTIVE
        await self.repository.save(existing)

        reason = build_detected_reason(candidate.explanation)
        await self.repository.add_history_event(
            AnomalyHistory(
                active_anomaly_id=existing.id,
                event_type=AnomalyEventType.DETECTED,
                old_severity=None,
                new_severity=candidate.severity,
                reason=reason,
                metrics_snapshot=_snapshot(candidate),
                event_timestamp=run_at,
            )
        )
        return AnomalyRunItem(anomaly=ActiveAnomalyResponse.model_validate(existing), reason=reason)

    async def _update_existing(
        self, existing: ActiveAnomaly, candidate: AnomalyCandidate, run_at: datetime
    ) -> Optional[AnomalyRunItem]:
        old_severity = existing.severity
        _apply_candidate(existing, candidate)
        existing.last_seen_at = run_at
        await self.repository.save(existing)

        if candidate.severity == old_severity:
            # Routine re-confirmation: values refreshed above, but nothing
            # meaningful changed, so no history row is written.
            return None

        reason = build_updated_reason(old_severity, candidate.severity, candidate.explanation)
        await self.repository.add_history_event(
            AnomalyHistory(
                active_anomaly_id=existing.id,
                event_type=AnomalyEventType.UPDATED,
                old_severity=old_severity,
                new_severity=candidate.severity,
                reason=reason,
                metrics_snapshot=_snapshot(candidate),
                event_timestamp=run_at,
            )
        )
        return AnomalyRunItem(anomaly=ActiveAnomalyResponse.model_validate(existing), reason=reason)

    async def _resolve(self, anomaly: ActiveAnomaly, run_at: datetime) -> AnomalyRunItem:
        anomaly.status = AnomalyStatus.RESOLVED
        await self.repository.save(anomaly)

        reason = build_resolved_reason(anomaly.entity_type, anomaly.entity_value)
        await self.repository.add_history_event(
            AnomalyHistory(
                active_anomaly_id=anomaly.id,
                event_type=AnomalyEventType.RESOLVED,
                old_severity=anomaly.severity,
                new_severity=None,
                reason=reason,
                metrics_snapshot=_snapshot_from_anomaly(anomaly),
                event_timestamp=run_at,
            )
        )
        return AnomalyRunItem(anomaly=ActiveAnomalyResponse.model_validate(anomaly), reason=reason)


def _apply_candidate(anomaly: ActiveAnomaly, candidate: AnomalyCandidate) -> None:
    anomaly.type = candidate.type
    anomaly.severity = candidate.severity
    anomaly.entity_type = candidate.entity_type
    anomaly.entity_value = candidate.entity_value
    anomaly.baseline_value = candidate.baseline_value
    anomaly.current_value = candidate.current_value
    anomaly.percentage_change = candidate.percentage_change
    anomaly.triggered_rule = candidate.triggered_rule
    anomaly.explanation = candidate.explanation


def _snapshot(candidate: AnomalyCandidate) -> dict:
    return {
        "type": candidate.type.value,
        "entity_type": candidate.entity_type,
        "entity_value": candidate.entity_value,
        "baseline_value": candidate.baseline_value,
        "current_value": candidate.current_value,
        "percentage_change": candidate.percentage_change,
        "severity": candidate.severity.value,
    }


def _snapshot_from_anomaly(anomaly: ActiveAnomaly) -> dict:
    severity: AnomalySeverity = anomaly.severity
    return {
        "type": anomaly.type.value,
        "entity_type": anomaly.entity_type,
        "entity_value": anomaly.entity_value,
        "baseline_value": anomaly.baseline_value,
        "current_value": anomaly.current_value,
        "percentage_change": anomaly.percentage_change,
        "severity": severity.value,
    }
