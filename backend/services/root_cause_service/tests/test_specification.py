from backend.services.root_cause_service.app.services.specification import (
    BillingCategorySpecification,
    CriticalSeveritySpecification,
    HighUrgencySpecification,
    InventoryCategorySpecification,
    LogisticsCategorySpecification,
    NegativeSentimentSpecification,
    OutageCategorySpecification,
    RegionalSpikeSpecification,
    SupportCategorySpecification,
    VolumeSpikeSpecification,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel


def test_billing_category_specification(make_incident):
    matching = make_incident(categories=(IssueCategory.PAYMENT_ISSUE,))
    other = make_incident(categories=(IssueCategory.DELIVERY_ISSUE,))
    spec = BillingCategorySpecification()
    assert spec.is_satisfied_by(matching) is True
    assert spec.is_satisfied_by(other) is False


def test_logistics_category_specification(make_incident):
    spec = LogisticsCategorySpecification()
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.DELIVERY_ISSUE,))) is True
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.SERVICE_DELAY,))) is True
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.PAYMENT_ISSUE,))) is False


def test_outage_category_specification(make_incident):
    spec = OutageCategorySpecification()
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.OPERATIONAL_FAILURE,))) is True
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.TECHNICAL_ISSUE,))) is True
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.PAYMENT_ISSUE,))) is False


def test_inventory_category_specification(make_incident):
    spec = InventoryCategorySpecification()
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.PRODUCT_ISSUE,))) is True
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.SUPPORT_ISSUE,))) is False


def test_support_category_specification(make_incident):
    spec = SupportCategorySpecification()
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.SUPPORT_ISSUE,))) is True
    assert spec.is_satisfied_by(make_incident(categories=(IssueCategory.PRODUCT_ISSUE,))) is False


def test_critical_severity_specification(make_incident):
    spec = CriticalSeveritySpecification()
    assert spec.is_satisfied_by(make_incident(severity=AnomalySeverity.CRITICAL)) is True
    assert spec.is_satisfied_by(make_incident(severity=AnomalySeverity.HIGH)) is False


def test_high_urgency_specification(make_incident):
    spec = HighUrgencySpecification()
    assert spec.is_satisfied_by(make_incident(urgency_levels=(UrgencyLabel.HIGH,))) is True
    assert spec.is_satisfied_by(make_incident(urgency_levels=(UrgencyLabel.CRITICAL,))) is True
    assert spec.is_satisfied_by(make_incident(urgency_levels=(UrgencyLabel.LOW,))) is False
    assert spec.is_satisfied_by(make_incident(urgency_levels=())) is False


def test_negative_sentiment_specification(make_incident):
    spec = NegativeSentimentSpecification()
    assert spec.is_satisfied_by(make_incident(anomaly_types=(AnomalyType.SENTIMENT_SHIFT,))) is True
    assert spec.is_satisfied_by(make_incident(anomaly_types=(AnomalyType.COMPLAINT_SPIKE,))) is False


def test_regional_spike_specification(make_incident):
    spec = RegionalSpikeSpecification()
    assert spec.is_satisfied_by(make_incident(anomaly_types=(AnomalyType.REGIONAL_SPIKE,))) is True
    assert spec.is_satisfied_by(make_incident(anomaly_types=())) is False


def test_volume_spike_specification(make_incident):
    spec = VolumeSpikeSpecification()
    assert spec.is_satisfied_by(make_incident(anomaly_types=(AnomalyType.COMPLAINT_SPIKE,))) is True
    assert spec.is_satisfied_by(make_incident(anomaly_types=())) is False


def test_and_combinator(make_incident):
    spec = CriticalSeveritySpecification() & BillingCategorySpecification()
    both = make_incident(severity=AnomalySeverity.CRITICAL, categories=(IssueCategory.PAYMENT_ISSUE,))
    only_severity = make_incident(severity=AnomalySeverity.CRITICAL, categories=(IssueCategory.DELIVERY_ISSUE,))
    assert spec.is_satisfied_by(both) is True
    assert spec.is_satisfied_by(only_severity) is False


def test_or_combinator(make_incident):
    spec = OutageCategorySpecification() | RegionalSpikeSpecification()
    category_only = make_incident(categories=(IssueCategory.TECHNICAL_ISSUE,))
    region_only = make_incident(anomaly_types=(AnomalyType.REGIONAL_SPIKE,))
    neither = make_incident()
    assert spec.is_satisfied_by(category_only) is True
    assert spec.is_satisfied_by(region_only) is True
    assert spec.is_satisfied_by(neither) is False


def test_not_combinator(make_incident):
    spec = ~CriticalSeveritySpecification()
    assert spec.is_satisfied_by(make_incident(severity=AnomalySeverity.CRITICAL)) is False
    assert spec.is_satisfied_by(make_incident(severity=AnomalySeverity.LOW)) is True
