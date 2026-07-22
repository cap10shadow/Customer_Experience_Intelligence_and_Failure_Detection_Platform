from typing import ClassVar

from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.domain.impact_rule import ImpactRule
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics
from backend.services.business_impact_service.app.services.scoring import escalate_level
from backend.shared.constants.enums.complaint import UrgencyLabel

CRITICAL_AFFECTED_CUSTOMERS_THRESHOLD = 1000
HIGH_AFFECTED_CUSTOMERS_THRESHOLD = 500
MEDIUM_AFFECTED_CUSTOMERS_THRESHOLD = 100


class CustomerRule(ImpactRule):
    """
    Customer Impact Rule

    Estimates customer-experience impact from how many customers the
    linked anomalies affected, escalated by one level when high/critical
    urgency signals are also present -- a large affected population that
    is also urgent hurts customers more than the same population at
    routine urgency.
    """

    DIMENSION: ClassVar[ImpactDimension] = ImpactDimension.CUSTOMER

    def evaluate(
        self,
        incident: Incident,
        root_cause: RootCauseSummary,
        trend_metrics: TrendMetrics,
        anomaly_metrics: AnomalyMetrics,
    ) -> ImpactEvaluation:
        affected = anomaly_metrics.affected_customer_count

        if affected <= 0:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.NONE,
                reason="No affected customers reported",
            )

        if affected >= CRITICAL_AFFECTED_CUSTOMERS_THRESHOLD:
            level = ImpactLevel.CRITICAL
        elif affected >= HIGH_AFFECTED_CUSTOMERS_THRESHOLD:
            level = ImpactLevel.HIGH
        elif affected >= MEDIUM_AFFECTED_CUSTOMERS_THRESHOLD:
            level = ImpactLevel.MEDIUM
        else:
            level = ImpactLevel.LOW

        high_urgency = UrgencyLabel.HIGH in incident.urgency_levels or UrgencyLabel.CRITICAL in incident.urgency_levels
        if high_urgency:
            level = escalate_level(level)
            reason = f"{affected} customers affected, escalated due to high/critical urgency signals"
        else:
            reason = f"{affected} customers affected"

        return ImpactEvaluation(impact_dimension=self.DIMENSION, impact_level=level, reason=reason)
