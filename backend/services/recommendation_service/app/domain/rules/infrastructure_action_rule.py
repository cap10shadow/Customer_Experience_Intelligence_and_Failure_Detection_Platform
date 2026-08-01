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

INFRASTRUCTURE_CATEGORIES = (IssueCategory.OPERATIONAL_FAILURE, IssueCategory.TECHNICAL_ISSUE)
MEANINGFUL_OPERATIONAL_IMPACT_LEVELS = ("high", "critical")
CRITICAL_OPERATIONAL_IMPACT_LEVELS = ("critical",)
INCIDENT_CATEGORY_EVIDENCE_WEIGHT = 10
OPERATIONAL_IMPACT_EVIDENCE_WEIGHT = 12


class InfrastructureActionRule(RecommendationRule):
    """
    Infrastructure Action Rule

    Fires when the Incident's complaint categories point to an operational
    failure or technical issue, or the business impact's operational
    dimension is high or critical -- both indicate the underlying systems,
    not just process, need direct remediation.
    """

    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        matched_categories = tuple(c for c in context.incident.categories if c in INFRASTRUCTURE_CATEGORIES)
        operational_impact_meaningful = (
            context.business_impact.operational_impact in MEANINGFUL_OPERATIONAL_IMPACT_LEVELS
        )

        if not matched_categories and not operational_impact_meaningful:
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
        if operational_impact_meaningful:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.BUSINESS_IMPACT,
                    description=(
                        f"Business impact operational dimension is {context.business_impact.operational_impact}"
                    ),
                    weight=OPERATIONAL_IMPACT_EVIDENCE_WEIGHT,
                )
            )

        priority = (
            RecommendationPriority.HIGH
            if context.business_impact.operational_impact in CRITICAL_OPERATIONAL_IMPACT_LEVELS
            else RecommendationPriority.MEDIUM
        )
        score = scoring.compute_score(priority, evidence)

        return (
            Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.INFRASTRUCTURE_ACTION,
                action="Initiate infrastructure diagnostics and remediation for the affected operational systems.",
                priority=priority,
                score=score,
                rationale="Operational-failure or technical-issue signals point to underlying infrastructure needing direct remediation.",
                priority_rationale="Critical operational impact warrants high urgency; otherwise medium urgency applies.",
                supporting_evidence=tuple(evidence),
            ),
        )
