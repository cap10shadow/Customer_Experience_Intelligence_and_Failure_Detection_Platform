from backend.services.anomaly_service.app.services.fingerprint import compute_fingerprint
from backend.shared.constants.enums.anomaly import AnomalyType


def test_fingerprint_is_stable_across_calls():
    fp1 = compute_fingerprint(AnomalyType.CATEGORY_SPIKE, "category", "billing")
    fp2 = compute_fingerprint(AnomalyType.CATEGORY_SPIKE, "category", "billing")
    assert fp1 == fp2


def test_fingerprint_differs_by_entity_value():
    fp_billing = compute_fingerprint(AnomalyType.CATEGORY_SPIKE, "category", "billing")
    fp_delivery = compute_fingerprint(AnomalyType.CATEGORY_SPIKE, "category", "delivery")
    assert fp_billing != fp_delivery


def test_fingerprint_differs_by_type():
    fp_category = compute_fingerprint(AnomalyType.CATEGORY_SPIKE, "region", "north")
    fp_region = compute_fingerprint(AnomalyType.REGIONAL_SPIKE, "region", "north")
    assert fp_category != fp_region


def test_fingerprint_handles_none_entity_value():
    fp1 = compute_fingerprint(AnomalyType.COMPLAINT_SPIKE, "global", None)
    fp2 = compute_fingerprint(AnomalyType.COMPLAINT_SPIKE, "global", None)
    assert fp1 == fp2
    assert "ALL" in fp1
