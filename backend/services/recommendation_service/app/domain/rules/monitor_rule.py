from typing import Tuple

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

LOW_SIGNAL_IMPACT_LEVELS = ("none", "low")
LOW_IMPACT_EVIDENCE_WEIGHT = 5


class MonitorRule(RecommendationRule):
    """
    Monitor Rule

    Fires as the baseline recommendation when business impact severity is
    none or low -- a low-signal incident still deserves an explicit
    recommendation (continue watching) rather than none at all.
    `RecommendationConsolidator` resolves the case where this and a more
    urgent category both fire for the same incident (see
    `recommendation_consolidator.py`).
    """

    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        if context.business_impact.overall_severity not in LOW_SIGNAL_IMPACT_LEVELS:
            return ()

        evidence = (
            SupportingEvidence(
                source=EvidenceSource.BUSINESS_IMPACT,
                description=f"Business impact overall severity is {context.business_impact.overall_severity}",
                weight=LOW_IMPACT_EVIDENCE_WEIGHT,
            ),
        )
        priority = RecommendationPriority.LOW
        score = scoring.compute_score(priority, evidence)

        return (
            Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.MONITOR,
                action="Continue monitoring the incident for escalation; no immediate action required.",
                priority=priority,
                score=score,
                rationale="Business impact severity is low or absent; no active response is currently warranted.",
                priority_rationale="Low-signal incidents warrant the lowest urgency tier.",
                supporting_evidence=evidence,
            ),
        )
