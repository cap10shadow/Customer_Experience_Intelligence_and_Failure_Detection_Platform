import uuid

from backend.services.root_cause_service.app.domain.root_cause_candidate import RootCauseCandidate
from backend.services.root_cause_service.app.models.root_cause import RootCause
from backend.shared.constants.enums.root_cause import RootCauseStatus


class RootCauseMapper:
    """
    RootCause Mapper

    Operational Purpose:
    Translates a `RootCauseCandidate` (the frozen Rule Engine's in-memory
    output) into a persistable `RootCause` ORM row for one Incident. The
    Rule Engine must never return or construct ORM objects — this mapper is
    the only place that boundary is crossed, in the opposite direction from
    `IncidentMapper`.

    Every field here is copied verbatim from the candidate; `evidence` is
    serialized to plain JSON-compatible dicts (one per Evidence value
    object) rather than normalized into relational tables.
    """

    @staticmethod
    def to_orm(incident_id: uuid.UUID, candidate: RootCauseCandidate) -> RootCause:
        return RootCause(
            incident_id=incident_id,
            cause=candidate.cause,
            confidence_score=candidate.confidence_score,
            confidence_level=candidate.confidence_level,
            evidence=[
                {"type": evidence_item.type.value, "description": evidence_item.description, "weight": evidence_item.weight}
                for evidence_item in candidate.evidence
            ],
            explanation=candidate.explanation,
            rule_version=candidate.rule_version,
            status=RootCauseStatus.IDENTIFIED,
        )
