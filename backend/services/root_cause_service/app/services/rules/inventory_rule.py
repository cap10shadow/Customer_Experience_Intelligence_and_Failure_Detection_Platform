from typing import ClassVar, Tuple

from backend.services.root_cause_service.app.domain.evidence import Evidence, EvidenceType
from backend.services.root_cause_service.app.domain.incident import Incident
from backend.services.root_cause_service.app.services.rule_engine import Rule, RuleResult
from backend.services.root_cause_service.app.services.scoring import (
    CATEGORY_MATCH_POINTS,
    HIGH_URGENCY_POINTS,
    VOLUME_SPIKE_POINTS,
    cap_score,
)
from backend.services.root_cause_service.app.services.specification import (
    HighUrgencySpecification,
    InventoryCategorySpecification,
    VolumeSpikeSpecification,
)
from backend.shared.constants.enums.root_cause import RootCause


class InventoryRule(Rule):
    """
    Inventory Shortage Rule

    Matches when the incident's complaints are concentrated in the product
    category. Confidence increases when reinforced by an overall complaint
    volume spike or high/critical urgency — consistent with widespread
    stock-outs or defective-batch shortages driving up complaint volume.
    """

    RULE_VERSION: ClassVar[str] = "1.0"
    CAUSE: ClassVar[RootCause] = RootCause.INVENTORY_SHORTAGE

    _category_spec = InventoryCategorySpecification()
    _volume_spec = VolumeSpikeSpecification()
    _urgency_spec = HighUrgencySpecification()

    def evaluate(self, incident: Incident) -> RuleResult:
        if not self._category_spec.is_satisfied_by(incident):
            return RuleResult(matched=False, cause=self.CAUSE, score=0, evidence=(), rule_version=self.RULE_VERSION)

        evidence: Tuple[Evidence, ...] = (
            Evidence(
                type=EvidenceType.CATEGORY,
                description="Product-related complaints are concentrated in this incident",
                weight=CATEGORY_MATCH_POINTS,
            ),
        )
        if self._volume_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(
                    type=EvidenceType.SUPPORTING_SIGNAL,
                    description="Overall complaint volume has spiked alongside product complaints",
                    weight=VOLUME_SPIKE_POINTS,
                ),
            )
        if self._urgency_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(type=EvidenceType.URGENCY, description="High or critical urgency signals are present", weight=HIGH_URGENCY_POINTS),
            )

        score = cap_score(sum(item.weight for item in evidence))
        return RuleResult(matched=True, cause=self.CAUSE, score=score, evidence=evidence, rule_version=self.RULE_VERSION)
