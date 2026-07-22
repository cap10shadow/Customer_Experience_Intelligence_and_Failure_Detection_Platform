from abc import ABC, abstractmethod

from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics


class ImpactRule(ABC):
    """
    Base for a single, independent business-impact rule.

    Architectural Boundaries:
    - A rule evaluates exactly one ImpactDimension.
    - A rule must be completely stateless and side-effect free, depending
      only on the Incident/RootCauseSummary/TrendMetrics/AnomalyMetrics it
      is given -- never persistence, never another service's API.
    - A rule must never call or depend on another ImpactRule; every rule is
      independently unit-testable in isolation.
    - The Business Impact Engine depends on this abstraction, never on
      concrete rule classes, so new dimensions can be added by registering
      another ImpactRule without modifying the engine.
    """

    @abstractmethod
    def evaluate(
        self,
        incident: Incident,
        root_cause: RootCauseSummary,
        trend_metrics: TrendMetrics,
        anomaly_metrics: AnomalyMetrics,
    ) -> ImpactEvaluation:
        """Evaluates this rule's dimension against the given inputs and returns its verdict."""
        raise NotImplementedError
