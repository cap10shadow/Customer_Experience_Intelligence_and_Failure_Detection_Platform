import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.services.recommendation_service.app.domain.anomaly_intelligence import AnomalyIntelligence
from backend.services.recommendation_service.app.domain.business_impact_summary import BusinessImpactSummary
from backend.services.recommendation_service.app.domain.incident import Incident
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.nlp_intelligence import NLPIntelligence
from backend.services.recommendation_service.app.domain.root_cause_summary import RootCauseSummary
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


class MalformedPayloadError(Exception):
    """Raised when a raw transport payload cannot be deserialized into a BusinessImpactCompletedPayload."""


@dataclass(frozen=True)
class BusinessImpactCompletedPayload:
    """
    BusinessImpactCompleted Transport Payload (Infrastructure-owned)

    Operational Purpose:
    The wire shape of the inbound `BusinessImpactCompleted` event, exactly
    as it arrives from outside this service -- a plain, untyped mapping of
    JSON-primitive fields, nested one level for `incident`/`business_impact`
    (required) and `root_cause`/`nlp_intelligence`/`anomaly_intelligence`
    (optional, matching their Optional status on `IntelligenceContext`
    itself). No such event schema exists anywhere else in this repository
    yet; this is Step 3's first definition of it, scoped to exactly what
    `BusinessImpactCompletedConsumer` needs to build an `IntelligenceContext`.

    Architectural Boundaries:
    - Lives in Infrastructure, never imported by Application or Domain --
      `BusinessImpactCompletedConsumer` is the only component that ever
      sees this shape; everything downstream only ever sees the
      Application-owned `RecommendationExecutionRequest`.
    - `from_raw()` is the Consumer's own "deserialize transport payload"
      and "validate transport schema" responsibility, expressed as a
      constructor: it performs no business validation (that remains
      Domain/Application's job) -- only the structural check of "are the
      required fields present and of a shape that can even be parsed,"
      raising `MalformedPayloadError` otherwise.
    """

    event_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    intelligence_context: IntelligenceContext

    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> "BusinessImpactCompletedPayload":
        try:
            event_id = uuid.UUID(str(raw["event_id"]))
            dataset_id = uuid.UUID(str(raw["dataset_id"]))
            dataset_version_id = uuid.UUID(str(raw["dataset_version_id"]))
            incident = BusinessImpactCompletedPayload._parse_incident(raw["incident"])
            business_impact = BusinessImpactCompletedPayload._parse_business_impact(raw["business_impact"])
            root_cause = BusinessImpactCompletedPayload._parse_root_cause(raw.get("root_cause"))
            nlp_intelligence = BusinessImpactCompletedPayload._parse_nlp_intelligence(raw.get("nlp_intelligence"))
            anomaly_intelligence = BusinessImpactCompletedPayload._parse_anomaly_intelligence(
                raw.get("anomaly_intelligence")
            )
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise MalformedPayloadError(f"Malformed BusinessImpactCompleted payload: {exc}") from exc

        try:
            context = IntelligenceContext(
                incident=incident,
                business_impact=business_impact,
                root_cause=root_cause,
                nlp_intelligence=nlp_intelligence,
                anomaly_intelligence=anomaly_intelligence,
            )
        except ValueError as exc:
            raise MalformedPayloadError(f"Malformed BusinessImpactCompleted payload: {exc}") from exc

        return BusinessImpactCompletedPayload(
            event_id=event_id, dataset_id=dataset_id, dataset_version_id=dataset_version_id, intelligence_context=context
        )

    @staticmethod
    def _parse_incident(payload: Dict[str, Any]) -> Incident:
        return Incident(
            incident_id=str(payload["incident_id"]),
            severity=AnomalySeverity(payload["severity"]),
            categories=tuple(IssueCategory(value) for value in payload.get("categories", ())),
            regions=tuple(str(value) for value in payload.get("regions", ())),
            urgency_levels=tuple(UrgencyLabel(value) for value in payload.get("urgency_levels", ())),
        )

    @staticmethod
    def _parse_business_impact(payload: Dict[str, Any]) -> BusinessImpactSummary:
        return BusinessImpactSummary(
            business_score=int(payload["business_score"]),
            overall_severity=str(payload["overall_severity"]),
            business_priority=str(payload["business_priority"]),
            confidence=int(payload["confidence"]),
            financial_impact=str(payload["financial_impact"]),
            customer_impact=str(payload["customer_impact"]),
            operational_impact=str(payload["operational_impact"]),
            sla_impact=str(payload["sla_impact"]),
            reputation_impact=str(payload["reputation_impact"]),
        )

    @staticmethod
    def _parse_root_cause(payload: Optional[Dict[str, Any]]) -> Optional[RootCauseSummary]:
        if payload is None:
            return None
        return RootCauseSummary(
            cause=RootCause(payload["cause"]),
            confidence_score=int(payload["confidence_score"]),
            confidence_level=str(payload["confidence_level"]),
        )

    @staticmethod
    def _parse_nlp_intelligence(payload: Optional[Dict[str, Any]]) -> Optional[NLPIntelligence]:
        if payload is None:
            return None
        return NLPIntelligence(
            sentiment_label=SentimentLabel(payload["sentiment_label"]),
            urgency_label=UrgencyLabel(payload["urgency_label"]),
            issue_category=IssueCategory(payload["issue_category"]),
            confidence_score=float(payload["confidence_score"]),
        )

    @staticmethod
    def _parse_anomaly_intelligence(payload: Optional[Dict[str, Any]]) -> Optional[AnomalyIntelligence]:
        if payload is None:
            return None
        return AnomalyIntelligence(
            anomaly_types=tuple(AnomalyType(value) for value in payload.get("anomaly_types", ())),
            severity=AnomalySeverity(payload["severity"]),
            affected_customer_count=int(payload["affected_customer_count"]),
            sla_breach_count=int(payload["sla_breach_count"]),
            negative_sentiment_ratio=float(payload.get("negative_sentiment_ratio", 0.0)),
        )
