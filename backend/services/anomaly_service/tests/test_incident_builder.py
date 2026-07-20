from backend.services.anomaly_service.app.services.incident_builder import (
    aggregate_severity,
    build_title,
    generate_incident_key,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity


def test_generate_incident_key_is_prefixed_and_unique():
    key1 = generate_incident_key()
    key2 = generate_incident_key()
    assert key1.startswith("INC-")
    assert key1 != key2


def test_aggregate_severity_picks_the_highest(make_anomaly):
    anomalies = [
        make_anomaly(severity=AnomalySeverity.LOW),
        make_anomaly(severity=AnomalySeverity.CRITICAL),
        make_anomaly(severity=AnomalySeverity.MEDIUM),
    ]
    assert aggregate_severity(anomalies) == AnomalySeverity.CRITICAL


def test_build_title_with_region_and_category(make_anomaly):
    anomalies = [
        make_anomaly(entity_type="region", entity_value="South"),
        make_anomaly(entity_type="category", entity_value="payment_issue"),
    ]
    assert build_title(anomalies) == "South — payment_issue Incident"


def test_build_title_with_region_only(make_anomaly):
    anomalies = [
        make_anomaly(entity_type="region", entity_value="South"),
        make_anomaly(entity_type="region", entity_value="South"),
    ]
    assert build_title(anomalies) == "South Regional Incident"


def test_build_title_with_category_only(make_anomaly):
    anomalies = [
        make_anomaly(entity_type="category", entity_value="payment_issue"),
        make_anomaly(entity_type="category", entity_value="payment_issue"),
    ]
    assert build_title(anomalies) == "payment_issue Category Incident"


def test_build_title_falls_back_to_generic(make_anomaly):
    anomalies = [make_anomaly(entity_type="global"), make_anomaly(entity_type="urgency", entity_value="critical")]
    assert build_title(anomalies) == "Multi-Signal Incident (2 anomalies)"
