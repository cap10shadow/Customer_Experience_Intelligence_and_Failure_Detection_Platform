from backend.services.anomaly_service.app.services.rules import region_rule
from backend.shared.constants.enums.anomaly import AnomalyType


def test_same_region_matches(make_anomaly):
    anomalies = [
        make_anomaly(type=AnomalyType.REGIONAL_SPIKE, entity_type="region", entity_value="South"),
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, entity_type="global", entity_value=None),
        make_anomaly(type=AnomalyType.URGENCY_SPIKE, entity_type="region", entity_value="South"),
    ]
    result = region_rule.evaluate(anomalies)
    assert result.matched is True
    assert result.points == 25
    assert "South" in result.reason


def test_different_regions_do_not_match(make_anomaly):
    anomalies = [
        make_anomaly(entity_type="region", entity_value="South"),
        make_anomaly(entity_type="region", entity_value="North"),
    ]
    result = region_rule.evaluate(anomalies)
    assert result.matched is False


def test_single_region_scoped_anomaly_does_not_match(make_anomaly):
    anomalies = [
        make_anomaly(entity_type="region", entity_value="South"),
        make_anomaly(entity_type="global", entity_value=None),
    ]
    result = region_rule.evaluate(anomalies)
    assert result.matched is False


def test_no_region_scoped_anomalies_does_not_match(make_anomaly):
    anomalies = [make_anomaly(entity_type="global"), make_anomaly(entity_type="category", entity_value="billing")]
    result = region_rule.evaluate(anomalies)
    assert result.matched is False
