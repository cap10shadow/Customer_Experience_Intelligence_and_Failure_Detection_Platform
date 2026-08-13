"""
Tests for backend/shared/observability/tracing.py (Phase 11 Batch 2).

Exercises real OpenTelemetry span generation -- a real `TracerProvider`,
real FastAPI/httpx auto-instrumentation, real requests via
`TestClient`/`ASGITransport` -- captured with OTel's own
`InMemorySpanExporter` test utility rather than mocking the tracing API
itself. No live OTel Collector/Tempo is required for these tests (that
dependency is confirmed separately via `init_tracing()`'s own exporter
wiring, which points at the real, configured OTLP endpoint); this file
verifies span *creation*, *attributes*, and *parent/child trace
continuity*, which is the actual Batch 2 behavior under test.
"""

import threading
import time

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from backend.shared.observability import tracing as tracing_module
from backend.shared.observability.correlation import CORRELATION_HEADER, CorrelationIdMiddleware
from backend.shared.observability.tracing import init_tracing


class _RealServer:
    """
    Runs a real FastAPI app on a real loopback TCP socket, in a
    background thread -- required because OpenTelemetry's httpx
    instrumentation wraps `httpx.HTTPTransport`/`AsyncHTTPTransport`
    (the real network transport classes) specifically, not
    `MockTransport`/`ASGITransport`. Verifying real client-span creation
    and real `traceparent` propagation therefore requires a real HTTP
    round-trip, not an in-process transport shortcut.
    """

    def __init__(self, app: FastAPI) -> None:
        config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="critical")
        self.server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> int:
        self._thread.start()
        for _ in range(200):
            if self.server.started:
                break
            time.sleep(0.02)
        return self.server.servers[0].sockets[0].getsockname()[1]

    def stop(self) -> None:
        self.server.should_exit = True
        self._thread.join(timeout=5)

_capture_exporter: InMemorySpanExporter = InMemorySpanExporter()
_capture_wired = False


def _ensure_real_provider_with_capture() -> InMemorySpanExporter:
    """
    Guarantees a real `TracerProvider` is the process-wide OTel provider
    (reusing whichever one Batch 2's `init_tracing()` already installed,
    if any service module has been imported this test session -- or
    creating one via the same code path if not), then attaches one
    additional `SimpleSpanProcessor(InMemorySpanExporter())` to it so
    tests can read back real, finished spans synchronously. Idempotent --
    safe to call from every test.
    """
    global _capture_wired
    provider = tracing_module._get_or_create_tracer_provider("test_service_tracing")
    if not _capture_wired:
        provider.add_span_processor(SimpleSpanProcessor(_capture_exporter))
        _capture_wired = True
    return _capture_exporter


@pytest.fixture(autouse=True)
def _clear_spans():
    _ensure_real_provider_with_capture()
    _capture_exporter.clear()
    yield
    _capture_exporter.clear()


def _build_app(service_name: str) -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    init_tracing(service_name, app)

    @app.get("/widgets/{widget_id}")
    def get_widget(widget_id: str):
        return {"id": widget_id}

    @app.get("/boom")
    def boom():
        raise RuntimeError("deliberate failure")

    return app


def test_tracing_initialization_sets_a_real_tracer_provider_with_the_service_name():
    provider = tracing_module._get_or_create_tracer_provider("test_service_tracing")
    assert isinstance(trace.get_tracer_provider(), TracerProvider)
    resource_attrs = dict(provider.resource.attributes)
    # The very first call in this process wins the service name (OTel's
    # provider is a true process-wide singleton) -- what matters here is
    # that a real, non-empty service.name was set, not which one, since
    # multiple services' modules may have already been imported this
    # test session.
    assert resource_attrs.get("service.name")


def test_incoming_request_creates_a_server_span_with_expected_attributes():
    exporter = _ensure_real_provider_with_capture()
    client = TestClient(_build_app("test_service_server_span"))

    client.get("/widgets/abc-123")

    server_spans = [s for s in exporter.get_finished_spans() if s.kind == trace.SpanKind.SERVER]
    assert len(server_spans) == 1
    span = server_spans[0]
    assert span.attributes.get("http.request.method") == "GET" or span.attributes.get("http.method") == "GET"
    status_code = span.attributes.get("http.response.status_code") or span.attributes.get("http.status_code")
    assert status_code == 200
    # Route template, not the raw path with the identifier baked in.
    route = span.attributes.get("http.route")
    assert route == "/widgets/{widget_id}"


def test_request_id_is_attached_to_the_server_span():
    exporter = _ensure_real_provider_with_capture()
    client = TestClient(_build_app("test_service_reqid_span"))

    client.get("/widgets/abc", headers={CORRELATION_HEADER: "trace-reqid-test"})

    server_spans = [s for s in exporter.get_finished_spans() if s.kind == trace.SpanKind.SERVER]
    assert server_spans[0].attributes.get("request_id") == "trace-reqid-test"


def test_failed_request_produces_an_error_span():
    exporter = _ensure_real_provider_with_capture()
    client = TestClient(_build_app("test_service_error_span"), raise_server_exceptions=False)

    client.get("/boom")

    server_spans = [s for s in exporter.get_finished_spans() if s.kind == trace.SpanKind.SERVER]
    assert len(server_spans) == 1
    assert server_spans[0].status.status_code == StatusCode.ERROR


def test_outbound_httpx_call_creates_a_client_span_and_injects_traceparent():
    exporter = _ensure_real_provider_with_capture()
    if not tracing_module._httpx_instrumented:
        HTTPXClientInstrumentor().instrument()
        tracing_module._httpx_instrumented = True

    captured_headers = {}
    downstream_app = FastAPI()

    @downstream_app.get("/ping")
    def ping():
        return {"ok": True}

    # A real ASGI middleware (not a route handler) is the reliable place
    # to capture the real inbound headers httpx actually sent over the wire.
    @downstream_app.middleware("http")
    async def capture(request, call_next):
        captured_headers.update(dict(request.headers))
        return await call_next(request)

    server = _RealServer(downstream_app)
    port = server.start()
    try:
        async def run():
            async with httpx.AsyncClient() as client:
                return await client.get(f"http://127.0.0.1:{port}/ping")

        import asyncio

        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("outer-operation"):
            response = asyncio.run(run())
    finally:
        server.stop()

    assert response.status_code == 200
    client_spans = [s for s in exporter.get_finished_spans() if s.kind == trace.SpanKind.CLIENT]
    assert len(client_spans) >= 1
    assert "traceparent" in captured_headers


def test_gateway_to_downstream_trace_continuity():
    """
    The core Batch 2 requirement, verified over a real HTTP round-trip
    (real TCP socket, real network transport -- see `_RealServer`'s own
    docstring for why this is required for genuine verification): a
    request that fans out from one instrumented service to a second
    instrumented service produces ONE connected trace -- both server
    spans share the same trace_id.
    """
    exporter = _ensure_real_provider_with_capture()
    if not tracing_module._httpx_instrumented:
        HTTPXClientInstrumentor().instrument()
        tracing_module._httpx_instrumented = True

    downstream_app = FastAPI()
    downstream_app.add_middleware(CorrelationIdMiddleware)
    init_tracing("test_downstream_service", downstream_app)

    @downstream_app.get("/incidents")
    def list_incidents():
        return []

    downstream_server = _RealServer(downstream_app)
    downstream_port = downstream_server.start()

    upstream_app = FastAPI()
    upstream_app.add_middleware(CorrelationIdMiddleware)
    init_tracing("test_upstream_gateway", upstream_app)

    @upstream_app.get("/api/v1/dashboard")
    async def dashboard():
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:{downstream_port}/incidents")
            return response.json()

    try:
        client = TestClient(upstream_app)
        response = client.get("/api/v1/dashboard")
    finally:
        downstream_server.stop()

    assert response.status_code == 200
    server_spans = [s for s in exporter.get_finished_spans() if s.kind == trace.SpanKind.SERVER]
    assert len(server_spans) == 2
    trace_ids = {s.context.trace_id for s in server_spans}
    assert len(trace_ids) == 1, "Gateway and downstream server spans must share one trace_id"


def test_business_impact_event_delivery_trace_continuity():
    """
    The second representative flow (Phase 11 architecture F6):
    business_impact_service's direct, Gateway-independent event-delivery
    call to recommendation_service/evaluation_service must also produce
    one connected trace over a real HTTP round-trip -- verified the same
    way, since both services get identical instrumentation with no
    special-case code.
    """
    exporter = _ensure_real_provider_with_capture()
    if not tracing_module._httpx_instrumented:
        HTTPXClientInstrumentor().instrument()
        tracing_module._httpx_instrumented = True

    recommendation_app = FastAPI()
    recommendation_app.add_middleware(CorrelationIdMiddleware)
    init_tracing("test_recommendation_service", recommendation_app)

    @recommendation_app.post("/internal/events/business-impact-completed")
    def receive_event():
        return {"received": True}

    recommendation_server = _RealServer(recommendation_app)
    recommendation_port = recommendation_server.start()

    business_impact_app = FastAPI()
    business_impact_app.add_middleware(CorrelationIdMiddleware)
    init_tracing("test_business_impact_service", business_impact_app)

    @business_impact_app.post("/business-impact")
    async def create_assessment():
        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://127.0.0.1:{recommendation_port}/internal/events/business-impact-completed",
                json={"event_id": "evt-1"},
            )
        return {"created": True}

    try:
        client = TestClient(business_impact_app)
        response = client.post("/business-impact")
    finally:
        recommendation_server.stop()

    assert response.status_code == 200
    server_spans = [s for s in exporter.get_finished_spans() if s.kind == trace.SpanKind.SERVER]
    assert len(server_spans) == 2
    trace_ids = {s.context.trace_id for s in server_spans}
    assert len(trace_ids) == 1, "business_impact_service and recommendation_service spans must share one trace_id"


def test_span_attributes_never_contain_authorization_or_secret_values():
    exporter = _ensure_real_provider_with_capture()
    client = TestClient(_build_app("test_service_span_safety"))

    client.get("/widgets/abc", headers={"Authorization": "Bearer super-secret-token-value"})

    for span in exporter.get_finished_spans():
        for value in span.attributes.values():
            assert "super-secret-token-value" not in str(value)


def test_tracing_disabled_short_circuits_without_error(monkeypatch):
    monkeypatch.setattr("backend.shared.observability.tracing.settings.TRACING_ENABLED", False)
    app = FastAPI()
    # Must not raise even though no provider/exporter is configured.
    init_tracing("test_service_disabled", app)
