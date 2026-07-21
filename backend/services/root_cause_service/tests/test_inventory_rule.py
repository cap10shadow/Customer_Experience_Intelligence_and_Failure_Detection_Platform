from backend.services.root_cause_service.app.services.rules.inventory_rule import InventoryRule
from backend.shared.constants.enums.anomaly import AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


def test_does_not_match_without_product_category(make_incident):
    incident = make_incident(categories=(IssueCategory.SUPPORT_ISSUE,))
    result = InventoryRule().evaluate(incident)
    assert result.matched is False
    assert result.cause == RootCause.INVENTORY_SHORTAGE


def test_matches_on_product_category(make_incident):
    incident = make_incident(categories=(IssueCategory.PRODUCT_ISSUE,))
    result = InventoryRule().evaluate(incident)
    assert result.matched is True
    assert result.score == 40


def test_score_increases_with_volume_spike_and_urgency(make_incident):
    incident = make_incident(
        categories=(IssueCategory.PRODUCT_ISSUE,),
        anomaly_types=(AnomalyType.COMPLAINT_SPIKE,),
        urgency_levels=(UrgencyLabel.HIGH,),
    )
    result = InventoryRule().evaluate(incident)
    assert result.score == 40 + 10 + 20
    assert len(result.evidence) == 3
