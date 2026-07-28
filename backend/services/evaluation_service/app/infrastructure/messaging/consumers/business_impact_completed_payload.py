import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

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
    JSON-primitive fields. No such event schema exists anywhere else in
    this repository yet (there is no shared broker/contracts module in
    this codebase today); this is Step 3's first definition of it, scoped
    to exactly what `BusinessImpactCompletedConsumer` needs to translate
    into an `EvaluationExecutionRequest`.

    Architectural Boundaries:
    - Lives in Infrastructure, never imported by Application or Domain --
      `BusinessImpactCompletedConsumer` is the only component that ever
      sees this shape; everything downstream only ever sees the
      Application-owned `EvaluationExecutionRequest`.
    - `from_raw()` is the Consumer's own "deserialize transport payload"
      responsibility, expressed as a constructor: it performs no business
      validation (that remains Domain/Application's job) -- only the
      structural check of "are the required fields present and of a
      shape that can even be parsed," raising `MalformedPayloadError`
      otherwise.
    """

    event_id: uuid.UUID
    incident_id: str
    root_cause: RootCause
    root_cause_confidence_score: int
    root_cause_explanation: str
    root_cause_evidence_count: int
    root_cause_id: Optional[uuid.UUID]
    business_impact_overall_score: int
    business_impact_overall_severity: str
    business_impact_business_priority: str
    business_impact_confidence: int
    business_impact_explanation: str
    assessment_id: Optional[uuid.UUID]

    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> "BusinessImpactCompletedPayload":
        try:
            return BusinessImpactCompletedPayload(
                event_id=uuid.UUID(str(raw["event_id"])),
                incident_id=str(raw["incident_id"]),
                root_cause=RootCause(raw["root_cause"]),
                root_cause_confidence_score=int(raw["root_cause_confidence_score"]),
                root_cause_explanation=str(raw["root_cause_explanation"]),
                root_cause_evidence_count=int(raw["root_cause_evidence_count"]),
                root_cause_id=uuid.UUID(str(raw["root_cause_id"])) if raw.get("root_cause_id") else None,
                business_impact_overall_score=int(raw["business_impact_overall_score"]),
                business_impact_overall_severity=str(raw["business_impact_overall_severity"]),
                business_impact_business_priority=str(raw["business_impact_business_priority"]),
                business_impact_confidence=int(raw["business_impact_confidence"]),
                business_impact_explanation=str(raw["business_impact_explanation"]),
                assessment_id=uuid.UUID(str(raw["assessment_id"])) if raw.get("assessment_id") else None,
            )
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise MalformedPayloadError(f"Malformed BusinessImpactCompleted payload: {exc}") from exc
