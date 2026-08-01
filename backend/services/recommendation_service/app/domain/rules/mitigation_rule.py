from typing import Tuple

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

MITIGATION_CONFIDENCE_THRESHOLD = 70
MEANINGFUL_IMPACT_LEVELS = ("high", "critical")
ROOT_CAUSE_CONFIDENCE_EVIDENCE_WEIGHT = 15
BUSINESS_IMPACT_EVIDENCE_WEIGHT = 10


class MitigationRule(RecommendationRule):
    """
    Mitigation Rule

    Fires when a confident root cause is known (confidence score at or
    above `MITIGATION_CONFIDENCE_THRESHOLD`) and the business impact is
    high or critical -- confident enough to act directly against the
    identified cause, rather than continuing to investigate.
    """

    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        root_cause = context.root_cause
        if root_cause is None or root_cause.confidence_score < MITIGATION_CONFIDENCE_THRESHOLD:
            return ()
        if context.business_impact.overall_severity not in MEANINGFUL_IMPACT_LEVELS:
            return ()

        priority = (
            RecommendationPriority.CRITICAL
            if context.business_impact.overall_severity == "critical"
            else RecommendationPriority.HIGH
        )
        evidence = (
            SupportingEvidence(
                source=EvidenceSource.ROOT_CAUSE,
                description=(
                    f"Root cause identified as '{root_cause.cause.value}' with "
                    f"{root_cause.confidence_score}% confidence"
                ),
                weight=ROOT_CAUSE_CONFIDENCE_EVIDENCE_WEIGHT,
            ),
            SupportingEvidence(
                source=EvidenceSource.BUSINESS_IMPACT,
                description=f"Business impact overall severity is {context.business_impact.overall_severity}",
                weight=BUSINESS_IMPACT_EVIDENCE_WEIGHT,
            ),
        )
        score = scoring.compute_score(priority, evidence)

        return (
            Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.MITIGATE,
                action=f"Apply mitigation actions targeting the identified root cause ({root_cause.cause.value}).",
                priority=priority,
                score=score,
                rationale=(
                    f"A root cause was identified with sufficient confidence "
                    f"({root_cause.confidence_score}%) to act on directly, and business impact is meaningful."
                ),
                priority_rationale=(
                    f"Business impact severity ({context.business_impact.overall_severity}) "
                    "determines how urgently mitigation should proceed."
                ),
                supporting_evidence=evidence,
            ),
        )
