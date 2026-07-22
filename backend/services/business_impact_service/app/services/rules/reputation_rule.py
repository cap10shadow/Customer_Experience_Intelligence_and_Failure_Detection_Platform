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
from backend.shared.constants.enums.anomaly import AnomalyType

HIGH_NEGATIVE_SENTIMENT_RATIO = 0.6
MEDIUM_NEGATIVE_SENTIMENT_RATIO = 0.3
MULTI_REGION_THRESHOLD = 2


class ReputationRule(ImpactRule):
    """
    Reputation Impact Rule

    Estimates public/brand reputational risk from the ratio of negative
    sentiment among affected complaints, escalated by one level when the
    decline is also confirmed by a SENTIMENT_SHIFT anomaly and/or the
    incident spans multiple regions -- broad, confirmed sentiment
    deterioration is what actually surfaces publicly.
    """

    DIMENSION: ClassVar[ImpactDimension] = ImpactDimension.REPUTATION

    def evaluate(
        self,
        incident: Incident,
        root_cause: RootCauseSummary,
        trend_metrics: TrendMetrics,
        anomaly_metrics: AnomalyMetrics,
    ) -> ImpactEvaluation:
        ratio = anomaly_metrics.negative_sentiment_ratio

        if ratio <= 0:
            return ImpactEvaluation(
                impact_dimension=self.DIMENSION,
                impact_level=ImpactLevel.NONE,
                reason="No negative sentiment signal detected",
            )

        if ratio >= HIGH_NEGATIVE_SENTIMENT_RATIO:
            level = ImpactLevel.HIGH
        elif ratio >= MEDIUM_NEGATIVE_SENTIMENT_RATIO:
            level = ImpactLevel.MEDIUM
        else:
            level = ImpactLevel.LOW

        confirmed_shift = AnomalyType.SENTIMENT_SHIFT in anomaly_metrics.anomaly_types
        multi_region = len(incident.regions) >= MULTI_REGION_THRESHOLD

        reason_parts = [f"{ratio:.0%} negative sentiment ratio"]
        if confirmed_shift:
            level = escalate_level(level)
            reason_parts.append("confirmed by a sentiment-shift anomaly")
        if multi_region:
            level = escalate_level(level)
            reason_parts.append(f"spanning {len(incident.regions)} regions")

        return ImpactEvaluation(impact_dimension=self.DIMENSION, impact_level=level, reason=", ".join(reason_parts))
