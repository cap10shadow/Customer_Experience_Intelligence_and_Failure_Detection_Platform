from typing import ClassVar

from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.domain.impact_rule import ImpactRule
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics
from backend.shared.constants.enums.anomaly import AnomalySeverity

CRITICAL_VOLUME_CHANGE_THRESHOLD = 50.0
HIGH_VOLUME_CHANGE_THRESHOLD = 30.0
MEDIUM_VOLUME_CHANGE_THRESHOLD = 15.0


class FinancialRule(ImpactRule):
    """
    Financial Impact Rule

    Estimates financial exposure (refunds, chargebacks, lost transactions)
    from the incident's severity, reinforced by complaint-volume growth
    (Phase 4 trend signal) -- a critical incident riding a large volume
    spike carries the highest revenue risk.
    """

    DIMENSION: ClassVar[ImpactDimension] = ImpactDimension.FINANCIAL

    def evaluate(
        self,
        incident: Incident,
        root_cause: RootCauseSummary,
        trend_metrics: TrendMetrics,
        anomaly_metrics: AnomalyMetrics,
    ) -> ImpactEvaluation:
        change = trend_metrics.percentage_change

        if incident.severity == AnomalySeverity.CRITICAL and change >= CRITICAL_VOLUME_CHANGE_THRESHOLD:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.CRITICAL,
                reason=f"Critical-severity incident with a {change:.0f}% complaint volume increase",
            )
        if incident.severity in (AnomalySeverity.CRITICAL, AnomalySeverity.HIGH) or change >= HIGH_VOLUME_CHANGE_THRESHOLD:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.HIGH,
                reason=f"High-severity incident or a {change:.0f}% complaint volume increase",
            )
        if incident.severity == AnomalySeverity.MEDIUM or change >= MEDIUM_VOLUME_CHANGE_THRESHOLD:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.MEDIUM,
                reason=f"Medium-severity incident or a {change:.0f}% complaint volume increase",
            )
        if change > 0:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.LOW,
                reason=f"Complaint volume increased by {change:.0f}%",
            )
        return ImpactEvaluation(
            impact_dimension=self.DIMENSION,
            impact_level=ImpactLevel.NONE,
            reason="No meaningful financial exposure signal detected",
        )
