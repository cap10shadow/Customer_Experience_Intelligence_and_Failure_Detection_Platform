from typing import List, Tuple

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence
from backend.shared.constants.enums.complaint import IssueCategory

OPERATIONAL_PROCESS_CATEGORIES = (
    IssueCategory.ACCOUNT_ISSUE,
    IssueCategory.SUBSCRIPTION_ISSUE,
    IssueCategory.REFUND_ISSUE,
)
MODERATE_OPERATIONAL_IMPACT_LEVELS = ("medium",)
INCIDENT_CATEGORY_EVIDENCE_WEIGHT = 8
OPERATIONAL_IMPACT_EVIDENCE_WEIGHT = 8


class OperationalActionRule(RecommendationRule):
    """
    Operational Action Rule

    Fires when the Incident's complaint categories point to a procedural
    concern (account, subscription, or refund handling), or the business
    impact's operational dimension is medium -- lighter-weight process
    action, distinct from `InfrastructureActionRule`'s system-level
    remediation for high/critical operational impact.
    """

    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        matched_categories = tuple(c for c in context.incident.categories if c in OPERATIONAL_PROCESS_CATEGORIES)
        moderate_operational_impact = context.business_impact.operational_impact in MODERATE_OPERATIONAL_IMPACT_LEVELS

        if not matched_categories and not moderate_operational_impact:
            return ()

        evidence: List[SupportingEvidence] = []
        if matched_categories:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.INCIDENT,
                    description=f"Incident includes categories: {', '.join(c.value for c in matched_categories)}",
                    weight=INCIDENT_CATEGORY_EVIDENCE_WEIGHT,
                )
            )
        if moderate_operational_impact:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.BUSINESS_IMPACT,
                    description=(
                        f"Business impact operational dimension is {context.business_impact.operational_impact}"
                    ),
                    weight=OPERATIONAL_IMPACT_EVIDENCE_WEIGHT,
                )
            )

        priority = RecommendationPriority.MEDIUM
        score = scoring.compute_score(priority, evidence)

        return (
            Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.OPERATIONAL_ACTION,
                action="Coordinate an internal operational process review to address the contributing procedural gaps.",
                priority=priority,
                score=score,
                rationale="Procedural complaint categories or a medium operational impact indicate a process-level, not infrastructure-level, gap.",
                priority_rationale="Medium operational impact and procedural categories warrant medium urgency.",
                supporting_evidence=tuple(evidence),
            ),
        )
