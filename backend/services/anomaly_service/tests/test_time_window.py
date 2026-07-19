from datetime import timedelta

from backend.services.anomaly_service.app.utils.time_window import resolve_window


def test_resolve_window_spans_requested_days():
    window = resolve_window(30)
    assert (window.end - window.start) == timedelta(days=30)


def test_resolve_window_label_reflects_days():
    window = resolve_window(7)
    assert window.label == "Last 7 Days"


def test_resolve_window_end_is_after_start():
    window = resolve_window(90)
    assert window.end > window.start
