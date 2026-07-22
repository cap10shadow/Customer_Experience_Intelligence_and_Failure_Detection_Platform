from dataclasses import dataclass
from typing import Tuple

from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation


@dataclass(frozen=True)
class BusinessImpactProfile:
    """
    Aggregate of all five ImpactEvaluation objects for one Incident -- the
    complete impact profile before weighting is applied.
    """

    financial: ImpactEvaluation
    customer: ImpactEvaluation
    operational: ImpactEvaluation
    sla: ImpactEvaluation
    reputation: ImpactEvaluation

    def all_evaluations(self) -> Tuple[ImpactEvaluation, ...]:
        """Every evaluation in this profile, in canonical dimension order."""
        return (self.financial, self.customer, self.operational, self.sla, self.reputation)
