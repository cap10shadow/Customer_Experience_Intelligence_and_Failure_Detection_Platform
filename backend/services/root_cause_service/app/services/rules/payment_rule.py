from typing import ClassVar, Tuple

from backend.services.root_cause_service.app.domain.evidence import Evidence, EvidenceType
from backend.services.root_cause_service.app.domain.incident import Incident
from backend.services.root_cause_service.app.services.rule_engine import Rule, RuleResult
from backend.services.root_cause_service.app.services.scoring import (
    CATEGORY_MATCH_POINTS,
    CRITICAL_SEVERITY_POINTS,
    HIGH_URGENCY_POINTS,
    NEGATIVE_SENTIMENT_POINTS,
    cap_score,
)
from backend.services.root_cause_service.app.services.specification import (
    BillingCategorySpecification,
    CriticalSeveritySpecification,
    HighUrgencySpecification,
    NegativeSentimentSpecification,
)
from backend.shared.constants.enums.root_cause import RootCause


class PaymentRule(Rule):
    """
    Payment Gateway Failure Rule

    Matches when the incident's complaints are concentrated in the payment
    category. Confidence increases when reinforced by critical severity,
    high/critical urgency, or a negative sentiment shift — a real payment
    gateway outage typically shows billing complaints together with
    escalating urgency and souring sentiment.
    """

    RULE_VERSION: ClassVar[str] = "1.0"
    CAUSE: ClassVar[RootCause] = RootCause.PAYMENT_GATEWAY_FAILURE

    _category_spec = BillingCategorySpecification()
    _severity_spec = CriticalSeveritySpecification()
    _urgency_spec = HighUrgencySpecification()
    _sentiment_spec = NegativeSentimentSpecification()

    def evaluate(self, incident: Incident) -> RuleResult:
        if not self._category_spec.is_satisfied_by(incident):
            return RuleResult(matched=False, cause=self.CAUSE, score=0, evidence=(), rule_version=self.RULE_VERSION)

        evidence: Tuple[Evidence, ...] = (
            Evidence(
                type=EvidenceType.CATEGORY,
                description="Payment-related complaints are concentrated in this incident",
                weight=CATEGORY_MATCH_POINTS,
            ),
        )
        if self._severity_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(type=EvidenceType.SEVERITY, description="Incident severity is critical", weight=CRITICAL_SEVERITY_POINTS),
            )
        if self._urgency_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(type=EvidenceType.URGENCY, description="High or critical urgency signals are present", weight=HIGH_URGENCY_POINTS),
            )
        if self._sentiment_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(type=EvidenceType.SENTIMENT, description="Customer sentiment is deteriorating", weight=NEGATIVE_SENTIMENT_POINTS),
            )

        score = cap_score(sum(item.weight for item in evidence))
        return RuleResult(matched=True, cause=self.CAUSE, score=score, evidence=evidence, rule_version=self.RULE_VERSION)
