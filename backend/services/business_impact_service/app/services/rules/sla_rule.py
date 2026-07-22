from typing import ClassVar

from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.domain.impact_rule import ImpactRule
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics
from backend.shared.constants.enums.complaint import UrgencyLabel

CRITICAL_SLA_BREACH_THRESHOLD = 20
HIGH_SLA_BREACH_THRESHOLD = 10
MEDIUM_SLA_BREACH_THRESHOLD = 3


class SLARule(ImpactRule):
    """
    SLA Impact Rule

    Estimates service-level-agreement risk from the number of SLA breaches
    linked to this incident, reinforced by high/critical urgency signals --
    breaches under mounting urgency are the clearest sign of an SLA
    commitment at risk.
    """

    DIMENSION: ClassVar[ImpactDimension] = ImpactDimension.SLA

    def evaluate(
        self,
        incident: Incident,
        root_cause: RootCauseSummary,
        trend_metrics: TrendMetrics,
        anomaly_metrics: AnomalyMetrics,
    ) -> ImpactEvaluation:
        breaches = anomaly_metrics.sla_breach_count

        if breaches <= 0:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.NONE,
                reason="No SLA breaches reported",
            )

        if breaches >= CRITICAL_SLA_BREACH_THRESHOLD:
            level = ImpactLevel.CRITICAL
        elif breaches >= HIGH_SLA_BREACH_THRESHOLD:
            level = ImpactLevel.HIGH
        elif breaches >= MEDIUM_SLA_BREACH_THRESHOLD:
            level = ImpactLevel.MEDIUM
        else:
            level = ImpactLevel.LOW

        high_urgency = UrgencyLabel.HIGH in incident.urgency_levels or UrgencyLabel.CRITICAL in incident.urgency_levels
        reason = f"{breaches} SLA breach(es) recorded"
        if high_urgency:
            reason += ", reinforced by high/critical urgency signals"

        return ImpactEvaluation(impact_dimension=self.DIMENSION, impact_level=level, reason=reason)
