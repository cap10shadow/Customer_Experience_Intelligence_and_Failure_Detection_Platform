from typing import Tuple

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

INVESTIGATION_CONFIDENCE_THRESHOLD = 50
MEANINGFUL_IMPACT_LEVELS = ("high", "critical")
MISSING_ROOT_CAUSE_EVIDENCE_WEIGHT = 10
LOW_CONFIDENCE_EVIDENCE_WEIGHT = 10


class InvestigateRule(RecommendationRule):
    """
    Investigate Rule

    Fires when no root cause is known yet, or the known root cause's
    confidence falls below `INVESTIGATION_CONFIDENCE_THRESHOLD` -- the
    intelligence available is not yet sufficient to commit to a mitigation
    path, so further investigation is the correct recommendation.
    """

    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        root_cause = context.root_cause
        insufficient_root_cause = root_cause is None or root_cause.confidence_score < INVESTIGATION_CONFIDENCE_THRESHOLD

        if not insufficient_root_cause:
            return ()

        if root_cause is None:
            evidence = (
                SupportingEvidence(
                    source=EvidenceSource.ROOT_CAUSE,
                    description="No root cause has been identified for this incident yet",
                    weight=MISSING_ROOT_CAUSE_EVIDENCE_WEIGHT,
                ),
            )
        else:
            evidence = (
                SupportingEvidence(
                    source=EvidenceSource.ROOT_CAUSE,
                    description=(
                        f"Root cause confidence ({root_cause.confidence_score}%) is below the "
                        f"{INVESTIGATION_CONFIDENCE_THRESHOLD}% threshold required to act on it directly"
                    ),
                    weight=LOW_CONFIDENCE_EVIDENCE_WEIGHT,
                ),
            )

        priority = (
            RecommendationPriority.MEDIUM
            if context.business_impact.overall_severity in MEANINGFUL_IMPACT_LEVELS
            else RecommendationPriority.LOW
        )
        score = scoring.compute_score(priority, evidence)

        return (
            Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.INVESTIGATE,
                action="Conduct further investigation to establish or confirm the root cause before committing to a mitigation path.",
                priority=priority,
                score=score,
                rationale="Root cause intelligence is missing or not yet confident enough to act on directly.",
                priority_rationale=(
                    "A high/critical business impact raises investigation urgency to medium; "
                    "otherwise low urgency applies."
                ),
                supporting_evidence=evidence,
            ),
        )
