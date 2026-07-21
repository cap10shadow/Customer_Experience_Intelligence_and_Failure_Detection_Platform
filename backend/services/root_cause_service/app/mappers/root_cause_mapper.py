import uuid
from typing import Any, Dict, List

from backend.services.root_cause_service.app.domain.root_cause_candidate import RootCauseCandidate
from backend.services.root_cause_service.app.models.root_cause import RootCause
from backend.shared.constants.enums.root_cause import RootCauseStatus


class RootCauseMapper:
    """
    RootCause Mapper

    Operational Purpose:
    Translates a `RootCauseCandidate` (the frozen Rule Engine's in-memory
    output) into persistable `RootCause` fields. The Rule Engine must never
    return or construct ORM objects — this mapper is the only place that
    boundary is crossed, in the opposite direction from `IncidentMapper`.

    Every field here is copied verbatim from the candidate; `evidence` is
    serialized to plain JSON-compatible dicts (one per Evidence value
    object) rather than normalized into relational tables.
    """

    @staticmethod
    def to_orm(incident_id: uuid.UUID, candidate: RootCauseCandidate) -> RootCause:
        """Builds a brand-new RootCause row for an Incident being analyzed for the first time."""
        return RootCause(
            incident_id=incident_id,
            cause=candidate.cause,
            confidence_score=candidate.confidence_score,
            confidence_level=candidate.confidence_level,
            evidence=RootCauseMapper._serialize_evidence(candidate),
            explanation=candidate.explanation,
            rule_version=candidate.rule_version,
            status=RootCauseStatus.IDENTIFIED,
        )

    @staticmethod
    def apply(root_cause: RootCause, candidate: RootCauseCandidate) -> RootCause:
        """
        Applies a freshly-computed RootCauseCandidate onto an already-persisted
        RootCause row (used by Phase 6 Step 3's refresh operation). Updates
        only the analysis fields — `id`, `incident_id`, `created_at`, and
        `status` are left untouched; lifecycle status is the Application
        Service's responsibility, not this mapper's.
        """
        root_cause.cause = candidate.cause
        root_cause.confidence_score = candidate.confidence_score
        root_cause.confidence_level = candidate.confidence_level
        root_cause.evidence = RootCauseMapper._serialize_evidence(candidate)
        root_cause.explanation = candidate.explanation
        root_cause.rule_version = candidate.rule_version
        return root_cause

    @staticmethod
    def _serialize_evidence(candidate: RootCauseCandidate) -> List[Dict[str, Any]]:
        return [
            {"type": evidence_item.type.value, "description": evidence_item.description, "weight": evidence_item.weight}
            for evidence_item in candidate.evidence
        ]
