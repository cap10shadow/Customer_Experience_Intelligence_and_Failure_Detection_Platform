from typing import ClassVar, FrozenSet

from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.domain.impact_rule import ImpactRule
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.root_cause import RootCause

# Root causes that directly interrupt internal operations (as opposed to
# e.g. payment or support-experience causes, which are financially/
# customer-impactful but do not by themselves halt operations).
_HIGH_OPERATIONAL_CAUSES: FrozenSet[RootCause] = frozenset({RootCause.SERVICE_OUTAGE, RootCause.INVENTORY_SHORTAGE})


class OperationalRule(ImpactRule):
    """
    Operational Impact Rule

    Estimates disruption to internal operations from the identified root
    cause -- a service outage or inventory shortage directly interrupts
    operations, reinforced by the underlying anomaly severity.
    """

    DIMENSION: ClassVar[ImpactDimension] = ImpactDimension.OPERATIONAL

    def evaluate(
        self,
        incident: Incident,
        root_cause: RootCauseSummary,
        trend_metrics: TrendMetrics,
        anomaly_metrics: AnomalyMetrics,
    ) -> ImpactEvaluation:
        is_operational_cause = root_cause.cause in _HIGH_OPERATIONAL_CAUSES

        if is_operational_cause and anomaly_metrics.severity == AnomalySeverity.CRITICAL:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.CRITICAL,
                reason=f"{root_cause.cause.value} identified with critical anomaly severity",
            )
        if is_operational_cause and anomaly_metrics.severity == AnomalySeverity.HIGH:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.HIGH,
                reason=f"{root_cause.cause.value} identified with high anomaly severity",
            )
        if is_operational_cause:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.MEDIUM,
                reason=f"{root_cause.cause.value} identified as the root cause",
            )
        if anomaly_metrics.severity in (AnomalySeverity.HIGH, AnomalySeverity.CRITICAL):
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.LOW,
                reason="Elevated anomaly severity without a directly operational root cause",
            )
        return ImpactEvaluation(
            impact_dimension=self.DIMENSION,
            impact_level=ImpactLevel.NONE,
            reason="No meaningful operational disruption signal detected",
        )
