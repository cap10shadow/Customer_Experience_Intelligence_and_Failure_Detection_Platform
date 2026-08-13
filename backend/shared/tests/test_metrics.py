"""
Tests for backend/shared/observability/metrics.py (Phase 11 Batch 1).
Exercises real runtime instrumentation -- a real FastAPI app, real
requests via TestClient, and reads the actual Prometheus metric values
(no static/fabricated numbers) via each metric's own `.labels(...)`
accessor.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.shared.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
    instrument_app,
)


def _counter_value(service: str, method: str, route: str, status_code: str) -> float:
    return HTTP_REQUESTS_TOTAL.labels(service=service, method=method, route=route, status_code=status_code)._value.get()


def _build_app(service_name: str) -> FastAPI:
    app = FastAPI()
    instrument_app(app, service_name=service_name)

    @app.get("/widgets/{widget_id}")
    def get_widget(widget_id: str):
        return {"id": widget_id}

    @app.get("/boom")
    def boom():
        raise RuntimeError("deliberate failure")

    return app


def test_metrics_endpoint_exists_and_returns_prometheus_exposition_format():
    client = TestClient(_build_app("test_service_metrics_endpoint"))

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


def test_a_real_request_increments_the_request_counter_with_the_route_template():
    service = "test_service_counter"
    client = TestClient(_build_app(service))
    before = _counter_value(service, "GET", "/widgets/{widget_id}", "200")

    client.get("/widgets/abc-123")
    client.get("/widgets/xyz-999")

    after = _counter_value(service, "GET", "/widgets/{widget_id}", "200")
    assert after == before + 2


def test_route_label_is_the_path_template_not_the_raw_url_with_the_identifier():
    """Metrics Label Discipline: the route label must stay bounded regardless of how many distinct widget IDs are requested."""
    service = "test_service_cardinality"
    client = TestClient(_build_app(service))

    client.get("/widgets/id-one")
    client.get("/widgets/id-two")
    client.get("/widgets/id-three")

    # All three real, distinct requests collapse into the same one bounded label combination.
    assert _counter_value(service, "GET", "/widgets/{widget_id}", "200") >= 3
    metrics_text = client.get("/metrics").text
    assert "id-one" not in metrics_text
    assert "id-two" not in metrics_text
    assert "id-three" not in metrics_text


def test_unmatched_route_is_recorded_under_a_single_bounded_bucket():
    service = "test_service_unmatched"
    client = TestClient(_build_app(service))

    client.get("/this-path-does-not-exist")
    client.get("/neither-does-this-one")

    assert _counter_value(service, "GET", "unmatched", "404") >= 2


def test_duration_histogram_records_a_real_observation():
    service = "test_service_duration"
    client = TestClient(_build_app(service))
    child = HTTP_REQUEST_DURATION_SECONDS.labels(service=service, method="GET", route="/widgets/{widget_id}")
    before_sum = child._sum.get()

    client.get("/widgets/abc")

    after_sum = child._sum.get()
    assert after_sum > before_sum


def test_in_progress_gauge_returns_to_zero_after_the_request_completes():
    service = "test_service_in_progress"
    client = TestClient(_build_app(service))

    client.get("/widgets/abc")

    assert HTTP_REQUESTS_IN_PROGRESS.labels(service=service)._value.get() == 0


def test_an_unhandled_exception_is_still_recorded_and_still_propagates():
    """Metrics collection must never swallow or alter existing error behavior."""
    service = "test_service_error"
    client = TestClient(_build_app(service), raise_server_exceptions=False)
    before = _counter_value(service, "GET", "/boom", "500")

    response = client.get("/boom")

    assert response.status_code == 500
    after = _counter_value(service, "GET", "/boom", "500")
    assert after == before + 1


# ---------------------------------------------------------------------------
# Phase 11 closure -- optional `refresh_readiness` hook
# ---------------------------------------------------------------------------


def test_metrics_scrape_awaits_the_refresh_readiness_hook_when_provided():
    calls = []

    async def _refresh():
        calls.append(1)

    app = FastAPI()
    instrument_app(app, service_name="test_service_readiness_hook", refresh_readiness=_refresh)
    client = TestClient(app)

    client.get("/metrics")

    assert calls == [1]


def test_metrics_scrape_works_without_a_refresh_readiness_hook():
    """gateway_service (no database) never passes this hook -- /metrics must
    keep working exactly as before when it's omitted."""
    app = FastAPI()
    instrument_app(app, service_name="test_service_no_hook")
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
