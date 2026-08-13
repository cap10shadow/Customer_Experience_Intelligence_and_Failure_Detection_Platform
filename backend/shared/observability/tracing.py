from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from backend.shared.config.settings import settings

if TYPE_CHECKING:
    # Type-only: `gateway_service` has no database engine of its own
    # (Phase 11 architecture §3.7) and its `requirements.txt` correctly
    # never installs `sqlalchemy` -- `from __future__ import annotations`
    # (above) makes this a deferred/string annotation, so it's never
    # evaluated at runtime, keeping this shared module (imported by all 9
    # services) importable in `gateway_service`.
    from sqlalchemy.ext.asyncio import AsyncEngine

# Process-global instrumentation state (Phase 11 Batch 2). Each of the 9
# services is its own process, so these guards only need to prevent a
# *within-process* double-instrumentation (e.g. two test apps in the
# same pytest run reusing the one shared `engine`/httpx instrumentor) --
# never a cross-service concern.
_tracer_provider: Optional[TracerProvider] = None
_httpx_instrumented = False
_instrumented_sync_engine_ids: set = set()


def _get_or_create_tracer_provider(service_name: str) -> TracerProvider:
    global _tracer_provider
    if _tracer_provider is None:
        resource = Resource.create({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.OTLP_EXPORTER_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer_provider = provider
    return _tracer_provider


def init_tracing(service_name: str, app: FastAPI, *, engine: Optional[AsyncEngine] = None) -> None:
    """
    Configures the OTel SDK once per process (OTLP exporter -> the
    `otel-collector`) and applies the standard, off-the-shelf
    auto-instrumentors -- Phase 11 Batch 2 (Phase 11 architecture §3.6).
    Called once per service, at module scope right after `app = FastAPI(
    ...)` is constructed (before the app starts serving) -- the same
    "startup instrumentation" section Batch 1's `CorrelationIdMiddleware`/
    `instrument_app` (metrics) calls already live in, so every service's
    observability wiring stays in one place.

    No manual span-creation code is required anywhere for the baseline:
    - FastAPI/ASGI instrumentation creates one server span per inbound
      HTTP request.
    - httpx instrumentation creates one client span per outbound HTTP
      call and injects the standard W3C `traceparent` header automatically
      -- this is what makes "Gateway -> downstream service" and
      "business_impact_service -> recommendation_service/evaluation_service"
      (Step 7.X's event-delivery hop) both appear as one connected,
      parent/child trace, with zero service-specific tracing code.
    - SQLAlchemy instrumentation (when `engine` is supplied -- the 8
      database-backed services) creates a child span per DB statement
      under whatever server/client span triggered it.

    Silently returns without configuring anything when tracing is
    disabled (`TRACING_ENABLED=false`) -- e.g. for a test process that
    never wants to reach an OTLP endpoint.
    """
    if not settings.TRACING_ENABLED:
        return

    _get_or_create_tracer_provider(service_name)

    if not getattr(app.state, "otel_instrumented", False):
        FastAPIInstrumentor.instrument_app(app)
        app.state.otel_instrumented = True

    global _httpx_instrumented
    if not _httpx_instrumented:
        HTTPXClientInstrumentor().instrument()
        _httpx_instrumented = True

    if engine is not None:
        # Imported here, not at module scope: `gateway_service` has no
        # database engine of its own (Phase 11 architecture §3.7) and its
        # `requirements.txt` correctly never installs
        # `opentelemetry-instrumentation-sqlalchemy` -- a module-level
        # import would make this shared module, imported by all 9
        # services, fail to import at all in `gateway_service`.
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        sync_engine = engine.sync_engine
        if id(sync_engine) not in _instrumented_sync_engine_ids:
            SQLAlchemyInstrumentor().instrument(engine=sync_engine)
            _instrumented_sync_engine_ids.add(id(sync_engine))


def shutdown_tracing() -> None:
    """
    Flushes any buffered spans before process exit -- called from each
    service's `lifespan()` teardown, alongside the existing `engine.
    dispose()` call. A no-op when tracing was never initialized (e.g.
    `TRACING_ENABLED=false`).
    """
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
