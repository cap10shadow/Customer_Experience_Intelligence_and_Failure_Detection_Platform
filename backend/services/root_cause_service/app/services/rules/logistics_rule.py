from typing import ClassVar, Tuple

from backend.services.root_cause_service.app.domain.evidence import Evidence, EvidenceType
from backend.services.root_cause_service.app.domain.incident import Incident
from backend.services.root_cause_service.app.services.rule_engine import Rule, RuleResult
from backend.services.root_cause_service.app.services.scoring import (
    CATEGORY_MATCH_POINTS,
    HIGH_URGENCY_POINTS,
    REGIONAL_SPIKE_POINTS,
    cap_score,
)
from backend.services.root_cause_service.app.services.specification import (
    HighUrgencySpecification,
    LogisticsCategorySpecification,
    RegionalSpikeSpecification,
)
from backend.shared.constants.enums.root_cause import RootCause


class LogisticsRule(Rule):
    """
    Logistics Delay Rule

    Matches when the incident's complaints are concentrated in delivery or
    service-delay categories. Confidence increases when the delay is
    concentrated in a specific region or accompanied by high/critical
    urgency — consistent with a regional carrier or fulfillment delay.
    """

    RULE_VERSION: ClassVar[str] = "1.0"
    CAUSE: ClassVar[RootCause] = RootCause.LOGISTICS_DELAY

    _category_spec = LogisticsCategorySpecification()
    _regional_spec = RegionalSpikeSpecification()
    _urgency_spec = HighUrgencySpecification()

    def evaluate(self, incident: Incident) -> RuleResult:
        if not self._category_spec.is_satisfied_by(incident):
            return RuleResult(matched=False, cause=self.CAUSE, score=0, evidence=(), rule_version=self.RULE_VERSION)

        evidence: Tuple[Evidence, ...] = (
            Evidence(
                type=EvidenceType.CATEGORY,
                description="Delivery or service-delay complaints are concentrated in this incident",
                weight=CATEGORY_MATCH_POINTS,
            ),
        )
        if self._regional_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(type=EvidenceType.REGION, description="Delay is concentrated in a specific region", weight=REGIONAL_SPIKE_POINTS),
            )
        if self._urgency_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(type=EvidenceType.URGENCY, description="High or critical urgency signals are present", weight=HIGH_URGENCY_POINTS),
            )

        score = cap_score(sum(item.weight for item in evidence))
        return RuleResult(matched=True, cause=self.CAUSE, score=score, evidence=evidence, rule_version=self.RULE_VERSION)
