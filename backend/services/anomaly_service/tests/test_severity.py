from backend.services.anomaly_service.app.services.severity import (
    classify_severity,
    compute_percentage_change,
    evaluate_change,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity


def test_percentage_change_basic():
    assert compute_percentage_change(10, 12) == 20.0
    assert compute_percentage_change(10, 30) == 200.0
    assert compute_percentage_change(8, 28) == 250.0


def test_percentage_change_zero_baseline_zero_current_is_zero():
    assert compute_percentage_change(0, 0) == 0.0


def test_percentage_change_zero_baseline_nonzero_current_is_undefined():
    assert compute_percentage_change(0, 5) is None


def test_classify_severity_bands():
    assert classify_severity(0.0) == AnomalySeverity.NORMAL
    assert classify_severity(20.0) == AnomalySeverity.NORMAL  # inclusive boundary
    assert classify_severity(20.1) == AnomalySeverity.LOW
    assert classify_severity(50.0) == AnomalySeverity.LOW
    assert classify_severity(50.1) == AnomalySeverity.MEDIUM
    assert classify_severity(100.0) == AnomalySeverity.MEDIUM
    assert classify_severity(100.1) == AnomalySeverity.HIGH
    assert classify_severity(200.0) == AnomalySeverity.HIGH
    assert classify_severity(200.1) == AnomalySeverity.CRITICAL


def test_classify_severity_uses_magnitude_regardless_of_sign():
    assert classify_severity(-250.0) == AnomalySeverity.CRITICAL


def test_classify_severity_undefined_baseline_is_critical():
    assert classify_severity(None) == AnomalySeverity.CRITICAL


def test_evaluate_change_no_data_is_none():
    assert evaluate_change(0, 0, direction="increase") is None


def test_evaluate_change_ten_to_twelve_is_no_anomaly():
    # The contract's own worked example: a 20% increase must NOT be flagged.
    assert evaluate_change(10, 12, direction="increase") is None


def test_evaluate_change_ten_to_thirty_is_an_anomaly():
    result = evaluate_change(10, 30, direction="increase")
    assert result is not None
    percentage_change, severity = result
    assert percentage_change == 200.0
    assert severity == AnomalySeverity.HIGH


def test_evaluate_change_increase_direction_ignores_decreases():
    assert evaluate_change(30, 10, direction="increase") is None


def test_evaluate_change_decrease_direction_ignores_increases():
    assert evaluate_change(10, 30, direction="decrease") is None


def test_evaluate_change_decrease_direction_detects_decline():
    result = evaluate_change(1, -2, direction="decrease")
    assert result is not None
    percentage_change, severity = result
    assert percentage_change == -300.0
    assert severity == AnomalySeverity.CRITICAL
