from typing import Tuple

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence
from backend.shared.constants.enums.anomaly import AnomalySeverity

CRITICAL_SEVERITY_LEVELS = ("critical",)
CRITICAL_SEVERITY_EVIDENCE_WEIGHT = 20
CRITICAL_INCIDENT_SEVERITY_EVIDENCE_WEIGHT = 10


class EscalationRule(RecommendationRule):
    """
    Escalation Rule

    Fires when the Incident's business impact is classified CRITICAL, or
    the Incident itself carries CRITICAL operational severity -- both
    signals independently justify escalating to senior operations
    leadership rather than handling the incident through normal channels.
    """

    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        business_impact_critical = context.business_impact.overall_severity in CRITICAL_SEVERITY_LEVELS
        incident_critical = context.incident.severity == AnomalySeverity.CRITICAL

        if not business_impact_critical and not incident_critical:
            return ()

        evidence = []
        if business_impact_critical:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.BUSINESS_IMPACT,
                    description=(
                        f"Business impact overall severity is critical (score: "
                        f"{context.business_impact.business_score})"
                    ),
                    weight=CRITICAL_SEVERITY_EVIDENCE_WEIGHT,
                )
            )
        if incident_critical:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.INCIDENT,
                    description="Incident operational severity is critical",
                    weight=CRITICAL_INCIDENT_SEVERITY_EVIDENCE_WEIGHT,
                )
            )

        priority = RecommendationPriority.CRITICAL
        score = scoring.compute_score(priority, evidence)

        return (
            Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.ESCALATE,
                action="Escalate incident to senior operations leadership for immediate review.",
                priority=priority,
                score=score,
                rationale=(
                    "Business and/or operational severity has reached the critical threshold; "
                    "normal-channel handling is insufficient."
                ),
                priority_rationale="Critical severity signals warrant the highest urgency tier.",
                supporting_evidence=tuple(evidence),
            ),
        )
