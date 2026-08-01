from typing import List, Tuple

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

MEANINGFUL_SLA_IMPACT_LEVELS = ("high", "critical")
CRITICAL_SLA_IMPACT_LEVELS = ("critical",)
SLA_CRITICAL_BREACH_THRESHOLD = 3
SLA_BREACH_EVIDENCE_WEIGHT = 15
SLA_IMPACT_EVIDENCE_WEIGHT = 12


class SLAProtectionRule(RecommendationRule):
    """
    SLA Protection Rule

    Fires when active SLA breaches are already occurring, or the business
    impact's SLA dimension is high or critical -- either signal means
    contractual service-level commitments are at risk or already broken.
    """

    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        anomaly = context.anomaly_intelligence
        has_sla_breaches = anomaly is not None and anomaly.sla_breach_count > 0
        sla_impact_meaningful = context.business_impact.sla_impact in MEANINGFUL_SLA_IMPACT_LEVELS

        if not has_sla_breaches and not sla_impact_meaningful:
            return ()

        evidence: List[SupportingEvidence] = []
        if has_sla_breaches:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.ANOMALY_INTELLIGENCE,
                    description=f"{anomaly.sla_breach_count} active SLA breach(es) detected",
                    weight=SLA_BREACH_EVIDENCE_WEIGHT,
                )
            )
        if sla_impact_meaningful:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.BUSINESS_IMPACT,
                    description=f"Business impact SLA dimension is {context.business_impact.sla_impact}",
                    weight=SLA_IMPACT_EVIDENCE_WEIGHT,
                )
            )

        critical_breach_volume = anomaly is not None and anomaly.sla_breach_count >= SLA_CRITICAL_BREACH_THRESHOLD
        critical_sla_impact = context.business_impact.sla_impact in CRITICAL_SLA_IMPACT_LEVELS
        priority = (
            RecommendationPriority.CRITICAL
            if critical_breach_volume or critical_sla_impact
            else RecommendationPriority.HIGH
        )
        score = scoring.compute_score(priority, evidence)

        return (
            Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.SLA_PROTECTION,
                action="Trigger SLA protection protocol to prevent or remediate service-level breaches.",
                priority=priority,
                score=score,
                rationale="Active SLA breaches or a high/critical SLA impact dimension put contractual commitments at risk.",
                priority_rationale=(
                    f"{SLA_CRITICAL_BREACH_THRESHOLD}+ active breaches or a critical SLA impact "
                    "warrant the highest urgency; otherwise high urgency applies."
                ),
                supporting_evidence=tuple(evidence),
            ),
        )
