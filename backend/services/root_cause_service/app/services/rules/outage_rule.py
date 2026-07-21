from typing import ClassVar, Tuple

from backend.services.root_cause_service.app.domain.evidence import Evidence, EvidenceType
from backend.services.root_cause_service.app.domain.incident import Incident
from backend.services.root_cause_service.app.services.rule_engine import Rule, RuleResult
from backend.services.root_cause_service.app.services.scoring import (
    CATEGORY_MATCH_POINTS,
    CRITICAL_SEVERITY_POINTS,
    HIGH_URGENCY_POINTS,
    REGIONAL_SPIKE_POINTS,
    cap_score,
)
from backend.services.root_cause_service.app.services.specification import (
    CriticalSeveritySpecification,
    HighUrgencySpecification,
    OutageCategorySpecification,
    RegionalSpikeSpecification,
)
from backend.shared.constants.enums.root_cause import RootCause


class OutageRule(Rule):
    """
    Service Outage Rule

    Matches when the incident includes operational-failure/technical
    complaints, OR a regional complaint spike — a genuine service outage
    often manifests as either (or both). Confidence increases when
    reinforced by critical severity and high/critical urgency, the
    signature of a widespread, urgent operational failure.
    """

    RULE_VERSION: ClassVar[str] = "1.0"
    CAUSE: ClassVar[RootCause] = RootCause.SERVICE_OUTAGE

    _category_spec = OutageCategorySpecification()
    _regional_spec = RegionalSpikeSpecification()
    _severity_spec = CriticalSeveritySpecification()
    _urgency_spec = HighUrgencySpecification()

    def evaluate(self, incident: Incident) -> RuleResult:
        trigger_spec = self._category_spec | self._regional_spec
        if not trigger_spec.is_satisfied_by(incident):
            return RuleResult(matched=False, cause=self.CAUSE, score=0, evidence=(), rule_version=self.RULE_VERSION)

        evidence: Tuple[Evidence, ...] = ()
        if self._category_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(
                    type=EvidenceType.CATEGORY,
                    description="Operational-failure or technical complaints detected",
                    weight=CATEGORY_MATCH_POINTS,
                ),
            )
        if self._regional_spec.is_satisfied_by(incident):
            evidence += (
                Evidence(
                    type=EvidenceType.REGION,
                    description="Anomalies span a regional spike, consistent with a service outage",
                    weight=REGIONAL_SPIKE_POINTS,
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

        score = cap_score(sum(item.weight for item in evidence))
        return RuleResult(matched=True, cause=self.CAUSE, score=score, evidence=evidence, rule_version=self.RULE_VERSION)
