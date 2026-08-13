import time

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

# Common technical metrics only (Phase 11 architecture §"Metrics
# Architecture"): every service gets these three for free. Labels are
# deliberately bounded -- `service`/`method`/`route`/`status_code` only,
# never a request/incident/recommendation/user ID (Metrics Label
# Discipline) -- `route` is the matched route *template*
# (e.g. "/recommendations/{recommendation_id}"), not the raw URL, so the
# label cardinality never grows with the number of distinct resources
# requested.
#
# Domain/business-specific metrics (e.g. "recommendations_generated_total")
# are never defined here -- a service that wants one imports
# Counter/Histogram/Gauge from this module and defines/increments it in
# its own domain code, keeping this shared module free of business logic.
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled, by service/method/route/status",
    ["service", "method", "route", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds, by service/method/route",
    ["service", "method", "route"],
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being handled, by service",
    ["service"],
)


def route_template(request: Request) -> str:
    """
    The matched route's path template, never the raw URL -- see this
    module's own docstring on label discipline. Falls back to
    "unmatched" for a request where no route matched at all (a genuine
    404), which is itself a single bounded bucket, not one per bogus path.
    """
    route = request.scope.get("route")
    if route is not None and hasattr(route, "path"):
        return route.path
    return "unmatched"


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Records the three common technical metrics for every request this
    service handles. Never swallows an exception: a failure still records
    a (best-effort "500") observation in `finally` and then propagates
    unchanged, exactly as it would without this middleware -- metrics
    collection must never alter request/response behavior.
    """

    def __init__(self, app: ASGIApp, service_name: str) -> None:
        super().__init__(app)
        self._service_name = service_name

    async def dispatch(self, request: Request, call_next):
        HTTP_REQUESTS_IN_PROGRESS.labels(service=self._service_name).inc()
        start = time.perf_counter()
        status_code = "500"
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        finally:
            duration = time.perf_counter() - start
            route = route_template(request)
            HTTP_REQUESTS_IN_PROGRESS.labels(service=self._service_name).dec()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                service=self._service_name, method=request.method, route=route
            ).observe(duration)
            HTTP_REQUESTS_TOTAL.labels(
                service=self._service_name, method=request.method, route=route, status_code=status_code
            ).inc()


def metrics_response() -> Response:
    """Renders the current process's metrics in Prometheus exposition format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def instrument_app(app: FastAPI, service_name: str) -> None:
    """
    Mounts the shared HTTP metrics middleware and a `GET /metrics`
    endpoint on `app`. Called once per service, in main.py -- the one
    place each service's own identity (`service_name`) is already known
    (the same string each service's own `/health` route already returns
    as `"service"`). `/metrics` is a real backend-only endpoint; it is
    never routed through the frontend workspace architecture.
    """
    app.add_middleware(PrometheusMiddleware, service_name=service_name)

    @app.get("/metrics", include_in_schema=False)
    def _metrics() -> Response:
        return metrics_response()
