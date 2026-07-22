from typing import Dict, Sequence, Tuple

from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.business_impact_assessment import BusinessImpactAssessment
from backend.services.business_impact_service.app.domain.business_impact_profile import BusinessImpactProfile
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_rule import ImpactRule
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics
from backend.services.business_impact_service.app.services.explanation import build_explanation
from backend.services.business_impact_service.app.services.rules.customer_rule import CustomerRule
from backend.services.business_impact_service.app.services.rules.financial_rule import FinancialRule
from backend.services.business_impact_service.app.services.rules.operational_rule import OperationalRule
from backend.services.business_impact_service.app.services.rules.reputation_rule import ReputationRule
from backend.services.business_impact_service.app.services.rules.sla_rule import SLARule
from backend.services.business_impact_service.app.services.scoring import (
    classify_business_priority,
    classify_severity,
    compute_confidence,
)
from backend.services.business_impact_service.app.services.weighting import compute_business_score

# The five canonical dimensions BusinessImpactProfile is frozen to (Phase 7
# Step 1 architecture). The engine validates against this set rather than
# against concrete rule classes, so it never needs to know which rule
# produced which dimension.
_REQUIRED_DIMENSIONS: Tuple[ImpactDimension, ...] = (
    ImpactDimension.FINANCIAL,
    ImpactDimension.CUSTOMER,
    ImpactDimension.OPERATIONAL,
    ImpactDimension.SLA,
    ImpactDimension.REPUTATION,
)


def default_rules() -> Tuple[ImpactRule, ...]:
    """Builds the built-in Phase 7 Step 1 rule set, one per business impact dimension."""
    return (FinancialRule(), CustomerRule(), OperationalRule(), SLARule(), ReputationRule())


class BusinessImpactEngine:
    """
    Business Impact Analysis Engine

    Ownership:
    Owned by the Business Impact Service.

    Operational Purpose:
    Evaluates every supplied ImpactRule against a single Incident (plus its
    identified RootCause, trend metrics, and anomaly metrics), aggregates
    the results into a BusinessImpactProfile, applies deterministic
    weighting, and produces the final BusinessImpactAssessment with its
    explanation. Purely in-memory: never queries a database or any
    repository/API.

    Philosophy:
    - Deterministic only: no randomness, no ML, no probabilistic reasoning.
    - Open/closed: the engine depends only on the ImpactRule abstraction,
      never on concrete rule classes -- it is constructed with whatever
      rules it is given, so adding a new rule never requires editing this
      class.
    - Fully explainable: every dimension's verdict carries its own
      deterministic reason, and the final explanation only aggregates
      those reasons -- it never re-derives or duplicates rule logic.
    """

    def __init__(self, rules: Sequence[ImpactRule]) -> None:
        self._rules = tuple(rules)

    def analyze(
        self,
        incident: Incident,
        root_cause: RootCauseSummary,
        trend_metrics: TrendMetrics,
        anomaly_metrics: AnomalyMetrics,
    ) -> BusinessImpactAssessment:
        """Runs every registered rule against the given inputs and returns the final assessment."""
        evaluations = [rule.evaluate(incident, root_cause, trend_metrics, anomaly_metrics) for rule in self._rules]
        profile = self._build_profile(evaluations)

        business_score = compute_business_score(profile)
        overall_severity = classify_severity(business_score)
        business_priority = classify_business_priority(overall_severity)
        confidence = compute_confidence(profile)
        explanation = build_explanation(profile, business_score, overall_severity, business_priority)

        return BusinessImpactAssessment(
            incident_id=incident.incident_id,
            root_cause=root_cause.cause,
            overall_severity=overall_severity,
            business_priority=business_priority,
            business_score=business_score,
            confidence=confidence,
            financial_impact=profile.financial.impact_level,
            customer_impact=profile.customer.impact_level,
            operational_impact=profile.operational.impact_level,
            sla_impact=profile.sla.impact_level,
            reputation_impact=profile.reputation.impact_level,
            estimated_affected_customers=anomaly_metrics.affected_customer_count,
            explanation=explanation,
        )

    @staticmethod
    def _build_profile(evaluations: Sequence[ImpactEvaluation]) -> BusinessImpactProfile:
        by_dimension: Dict[ImpactDimension, ImpactEvaluation] = {}
        for evaluation in evaluations:
            if evaluation.impact_dimension in by_dimension:
                raise ValueError(f"Duplicate ImpactRule evaluation for dimension: {evaluation.impact_dimension.value}")
            by_dimension[evaluation.impact_dimension] = evaluation

        missing = [dimension for dimension in _REQUIRED_DIMENSIONS if dimension not in by_dimension]
        if missing:
            raise ValueError(f"Missing ImpactRule evaluation(s) for dimension(s): {[d.value for d in missing]}")

        return BusinessImpactProfile(
            financial=by_dimension[ImpactDimension.FINANCIAL],
            customer=by_dimension[ImpactDimension.CUSTOMER],
            operational=by_dimension[ImpactDimension.OPERATIONAL],
            sla=by_dimension[ImpactDimension.SLA],
            reputation=by_dimension[ImpactDimension.REPUTATION],
        )
