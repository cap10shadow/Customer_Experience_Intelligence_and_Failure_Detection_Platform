# Phase 11 — Observability & Reliability
# Final Architecture (Reviewed & Frozen)

**Status:** Architecture frozen. No implementation has occurred. No source code, tests, Docker Compose, or other project documentation was modified to produce this document.
**Date:** 2026-08-13
**Scope boundary:** Phase 10 and Step 7.X are complete and are not reopened. Phase 12 (AI Copilot) and Phase 13 (Production Hardening) are explicitly out of scope.

---

## 1. Review Result

**PASS WITH CHANGES.** The internally-reviewed architecture's stack choice, batch structure, and constraints are sound and correctly scoped to Phase 11. Repository inspection found six concrete, evidence-based issues — none invalidate the architecture; all are incorporated as corrections below (§3–§6) before freezing.

---

## 2. Findings

### F1 — Grafana's default port collides with the frontend
**Evidence:** `docker-compose.yml`, `frontend` service: `ports: ["${FRONTEND_PORT:-3000}:3000"]`. Grafana's default container port is also 3000.
**Severity:** Medium (would break `docker compose up` if both map their internal 3000 to host 3000).
**Resolution:** Grafana's host port mapping becomes `${GRAFANA_PORT:-3001}:3000` (container stays on its default internal 3000; only the host mapping changes) — same `${VAR:-default}` convention every existing service already uses in `docker-compose.yml`/`.env.example`.
**Changes architecture or implementation detail:** Implementation detail (port mapping only).

### F2 — The shared structured-logging module exists but is unused everywhere, and is not structured
**Evidence:** `backend/shared/logging/logger.py` defines `get_logger()`, but `grep -rl "get_logger" backend/services` (excluding tests) returns zero matches. No service calls it. Its output format is a plain string (`"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`), not JSON, and carries no `service`/`request_id` fields. The Gateway's own only log call (`logger.exception` in `core/errors.py`) uses raw `logging.getLogger(__name__)` directly, bypassing this module entirely.
**Severity:** Medium (this is exactly the extension point Phase 11 needs, but it must be rewritten, not merely wired in as-is; zero migration risk since nothing currently depends on its current output shape).
**Resolution:** Rewrite `backend/shared/logging/logger.py` in place to emit structured JSON (`timestamp`, `service`, `level`, `message`, `request_id` when available, plus safe extra fields) and read `request_id` from a contextvar (see F3). Every service's own `logging.getLogger(__name__)` call sites (currently only Gateway's) are migrated to call `get_logger(__name__)` instead. This is additive/corrective to an existing, already-designated module — not a new shared package for logging.
**Changes architecture or implementation detail:** Implementation detail (the module's designated role — "shared logging primitive" — was already correct; only its content and adoption are corrected).

### F3 — Correlation IDs exist only at the Gateway edge and are never forwarded downstream
**Evidence:** `CorrelationIdMiddleware` (`gateway_service/app/core/correlation.py`) assigns/reads `X-Request-ID` only on the Gateway's own inbound request; `gateway_service/app/core/downstream.py`'s `get_json`/`patch_json` (verified directly) construct outbound `client.get(...)`/`client.patch(...)` calls with no headers forwarded. No other service (`grep -rl "CorrelationIdMiddleware\|X-Request-ID"` across `backend/services`) references correlation at all. `business_impact_service`'s own outbound event-delivery call (to `recommendation_service`/`evaluation_service`) is a second, Gateway-independent HTTP hop with the same gap.
**Severity:** High for Phase 11's own stated goal (structured logs must carry a correlation/request ID per §9 of the task) — without this, per-request log correlation across services is impossible, and it is also the natural carrier for associating logs with the eventual trace ID.
**Resolution:** Promote correlation-ID assignment/propagation into a shared primitive (`backend/shared/observability/correlation.py`): a small ASGI middleware every service (not just Gateway) installs, storing `request_id` in a `contextvar` the shared logger reads. Gateway's `core/downstream.py` (and `business_impact_service`'s event-delivery client) are extended to forward `X-Request-ID` on every outbound call. Gateway's existing `core/correlation.py` is retired in favor of the shared module so there is exactly one correlation implementation, not two. This is the same header (`X-Request-ID`) and the same behavior Gateway already has today (reuse an inbound ID, generate one otherwise, echo it back) — generalized, not redesigned.
**Changes architecture or implementation detail:** Minor architecture clarification (the internal architecture said "correlation utilities" belong in shared code; this finding makes explicit that Gateway's existing correlation code must be consolidated into that shared module, and that propagation to downstream calls — not just assignment — is required).

### F4 — `/health` today is liveness-only; a real readiness/dependency-health endpoint does not exist anywhere
**Evidence:** Every service's `/health` route (`anomaly_service`, `recommendation_service`, `ingestion_service`, `copilot_service`, verified directly, and by pattern the remaining services) is a synchronous handler returning a hardcoded `{"status": "ok", "service": "..."}` with no dependency check. `backend/shared/database/health.py`'s `check_database_connection()` already exists and is real, but is invoked only once, at process startup inside each service's `lifespan()` (confirmed in `ingestion_service`, `copilot_service`) — never per-request. 8 of 9 services own a database connection (`gateway_service` is the sole exception — confirmed no `engine`/`get_db_session` import in its `main.py`, consistent with Batch 1's "Gateway does not own persistence").
**Severity:** Medium. This is not a gap the internal architecture missed (Batch 3 already scopes "standardized readiness, dependency health"); this finding just confirms the work is genuinely necessary, not redundant, and identifies the exact existing primitive (`check_database_connection()`) to reuse rather than reinvent.
**Resolution:** Add one new, additive endpoint per service — `GET /health/ready` — that calls `check_database_connection()` live and returns 200/503 accordingly, for the 8 services with a database; `gateway_service` keeps `/health` as its only endpoint (liveness only — it has no dependency of its own to check; Administration's existing Platform Overview aggregation, Step 7.X A-02, is a separate, product-facing consumer of `/health` and is explicitly not touched — see §8). The existing `/health` contract (used today by every service's own Docker healthcheck and by Administration's `/health` polling) is never modified, renamed, or removed.
**Changes architecture or implementation detail:** Implementation detail (confirms and grounds an already-scoped batch item; does not change the batch plan).

### F5 — Loki's log-ingestion mechanism must be Promtail-via-Docker-json-file-driver, not invented
**Evidence:** `docker-compose.yml` sets no `logging:` driver on any service, so every container uses Docker's default `json-file` driver, meaning every service's stdout (where the corrected structured logger writes, per F2) already lands in a well-known, discoverable location (`/var/lib/docker/containers/<id>/<id>-json.log`) with zero code change required to any service. No Fluentd/Fluent Bit/Vector/syslog dependency exists anywhere in this repository today, and none of the Docker Compose services push logs over the network.
**Severity:** Low (this is the "intentionally not yet frozen" mechanism the task explicitly asked to be resolved from the repository, not a defect).
**Resolution:** Use **Promtail** (Grafana's own log-shipper, purpose-built for exactly this: tailing Docker's `json-file` logs via `docker_sd_configs` container discovery and pushing to Loki) as one additional, internal-only Compose service. This requires zero application-code changes beyond making stdout structured (already required by F2) and is the smallest-footprint option consistent with "lightweight... appropriate for this prototype" (§4) — the alternative (each service pushing logs directly to Loki over the network) would add a logging-transport dependency to every service's `requirements.txt` and couple business logic to Loki's availability, which the task's "no premature infrastructure" and "shared code must not accumulate business logic" constraints both argue against.
**Changes architecture or implementation detail:** Architecture detail (resolves the deliberately-open question in §5 of the task; not a deviation from anything previously frozen).

### F6 — Business-impact/recommendation event delivery is a second, non-Gateway trace boundary that the original topology diagram omits
**Evidence:** `business_impact_service` delivers `BusinessImpactCompleted` via its own `httpx.AsyncClient` (`dependencies/services.py`, confirmed in Phase 10 Step 7 record) directly to `recommendation_service`'s and `evaluation_service`'s `/internal/events/*` routes — this HTTP call never passes through the Gateway. The original topology diagram (§2 of the task) shows only `Gateway → Backend Services` as the traced path.
**Severity:** Low (does not invalidate the architecture; the tracing library (OTel's httpx/FastAPI auto-instrumentation) will capture this hop automatically once `business_impact_service` and its two receivers are instrumented like every other service — no special-case code is needed), but the *verification plan* must explicitly include it, since "Gateway → downstream service" alone would never exercise this path.
**Resolution:** Batch 2's tracing verification explicitly includes a second representative trace: `business_impact_service → recommendation_service` (or `evaluation_service`) over `/internal/events/business-impact-completed`, in addition to the Gateway-initiated trace. No new component or code path is required — this falls out of instrumenting every service uniformly.
**Changes architecture or implementation detail:** Implementation/verification detail (adds a verification case; does not change the instrumentation architecture).

### Non-findings (explicitly checked, no issue)
- **Dockerfiles are mechanically uniform** across all 9 services (diffed `gateway_service` vs. `recommendation_service` Dockerfiles — only the service name/port differ) — confirms per-service `requirements.txt` + shared-code-copy pattern will scale identically to all 9 without special-casing.
- **No service currently has any observability dependency** (`grep -rli "prometheus|opentelemetry|otel|grafana|loki|tempo"` across every `requirements.txt` — zero matches) — this is a fully greenfield addition, not a migration.
- **The frontend already generates and surfaces `X-Request-ID`/`requestId`** (`frontend/src/app/api/client.ts`, `errors.ts`) end-to-end into `ApiError` — the "frontend boundary" requirement (§6 of the task) is therefore already substantially satisfied by Step 7 and needs no new frontend infrastructure, only confirmation that it is correctly forwarded once services propagate the same header (F3).
- **`backend/shared/database/database.py` exports one importable `engine`/`async_session_maker` pair** every service already imports — the correct, existing extension point for SQLAlchemy trace instrumentation and DB-pool metrics, requiring no per-service duplication.
- **ARCHITECTURE.md §10 ("Observability & Monitoring")** already names Prometheus, Grafana, structured logging, and distributed tracing as the intended future stack, and separately lists business-facing metrics (complaint spike frequency, recommendation generation frequency, root-cause confidence distribution, etc.) as service-owned — directly consistent with, and never contradicted by, the internal architecture's "shared code must not accumulate business logic" constraint.
- **Batch sequencing is sound**: Batch 1 (backend-only: logging, correlation, metrics, health foundation, Prometheus, Loki+Promtail) has no dependency on tracing and is independently verifiable; Batch 2 (tracing) benefits from Batch 1's correlation primitive but does not require it to function; Batch 3 (reliability/error visibility) can reuse Batch 1's metrics and optionally Batch 2's trace context but is not blocked by either; Batch 4 (Grafana) necessarily depends on all three since dashboards need real data to exist first. No batch was found to be implementable-but-unverifiable in isolation, and no batch was found to secretly require a later batch's output.
- **No Phase 12/13 scope creep found**: "AI copilot request tracing" (ARCHITECTURE.md §10) is not implemented as a copilot-specific feature — `copilot_service` is instrumented identically to every other scaffolded service (health/metrics/logs/traces), not given bespoke tracing logic, since it has no real routes yet (Phase 12). No JWT/RBAC/auth work appears anywhere in the batch plan (Phase 13).

---

## 3. Final Architecture

### 3.1 Topology

```
Frontend (existing X-Request-ID generation — unchanged)
   |
   v
Gateway  ── structured logs ──> stdout (json-file) ─┐
   |  \── metrics (/metrics) ──> Prometheus          │
   |   \── traces (OTLP) ───────> OTel Collector ──> Tempo
   | (X-Request-ID + trace context forwarded)        │
   v                                                  │
Backend Services (8) ── structured logs ──> stdout ──┤
   |         \── metrics (/metrics) ──> Prometheus    │      Promtail (tails
   |          \── traces (OTLP) ─────> OTel Collector │       Docker json-file
   |                                                   │       logs, container-
   v (event delivery, business_impact_service          │       discovery)
   -> recommendation_service / evaluation_service,      │            |
      same instrumentation, second trace boundary)      v            v
                                                       Loki <────────┘

Prometheus + Loki + Tempo
           |
           v
        Grafana (host port 3001 -- 3000 is the frontend's)
```

Only `gateway_service` (existing, unchanged), `postgres` (existing, unchanged), `frontend` (existing, unchanged), `prometheus`, and `grafana` are host-published. Every other service — the 7 already-internal-only backend services, plus the new `otel-collector`, `tempo`, `loki`, and `promtail` — remains reachable only over the Compose network, exactly matching the existing "internal-only, no host port mapping" convention already applied to `ingestion_service` through `evaluation_service`.

### 3.2 Component Responsibilities

| Component | Responsibility | Host port | Notes |
|---|---|---|---|
| Prometheus | Scrapes `/metrics` from all 9 backend services + itself | `9090` (dev convenience, optional) | Standard `docker_sd_configs`-free static scrape config listing the 9 known service:port pairs (mirrors `GatewaySettings.downstream_service_urls`'s existing enumeration) |
| Grafana | Dashboards over Prometheus/Loki/Tempo | `3001` (F1) | Provisioned datasources + the 2 dashboards (§3.9, amended by OBS-002), version-controlled as JSON |
| Loki | Log storage/query | internal only | Queried by Grafana over the Compose network |
| Promtail | Tails Docker `json-file` logs, ships to Loki | internal only | Reads `/var/lib/docker/containers` (read-only mount) — zero application code changes (F5) |
| OTel Collector | Receives OTLP from all services, forwards to Tempo | internal only | One collector, standard `otlp` receiver → `otlp` exporter pipeline |
| Tempo | Trace storage/query | internal only | Queried by Grafana and by the Collector's exporter |

### 3.3 Logging Architecture
- `backend/shared/logging/logger.py` (existing module, rewritten — F2) becomes the single structured-JSON logging primitive every service imports via `get_logger(__name__)`.
- Fields: `timestamp`, `service` (from each service's own settings/module name), `level`, `message`, `request_id` (from the shared correlation contextvar, §3.4 — omitted, not `null`-padded, when genuinely absent, e.g. during startup before a request exists), plus safe caller-supplied `extra` fields only (never raw exception objects, headers, or request bodies — see §3.7).
- Output remains stdout — no service gains a network logging dependency. Docker's default `json-file` driver + Promtail (F5) does the shipping.
- Domain-specific log content (e.g., "recommendation generated for incident X") is written by each service using the shared primitive, exactly as `get_logger(__name__).info(...)` already allows — the shared module owns *how* a log line is shaped, never *what* a service chooses to log.

### 3.4 Correlation Architecture
- `backend/shared/observability/correlation.py` (new shared module, generalized from Gateway's existing `core/correlation.py` — F3): one ASGI middleware, installed by every service, that reuses an inbound `X-Request-ID` or generates one, stores it in a `contextvar`, and echoes it on the response — identical behavior to what Gateway already does today, just no longer Gateway-only.
- Gateway's downstream calls (`core/downstream.py`'s `get_json`/`patch_json`) and `business_impact_service`'s event-delivery client both forward the current `X-Request-ID` as an outbound header (F3) — this is the one behavioral change to existing Gateway code this architecture requires, and it is additive (one new header on outbound calls), not a rewrite of downstream/error-handling logic.
- The same `request_id` is attached to the active trace span (as a span attribute) wherever tracing is active, giving a human a way to jump from one log line to its full distributed trace without needing the trace ID memorized.

### 3.5 Metrics Architecture
- `backend/shared/observability/metrics.py` (new shared module): a shared Prometheus `CollectorRegistry`, one FastAPI middleware providing the three **common technical metrics** every service gets for free — `http_requests_total{service,method,route,status}`, `http_request_duration_seconds{service,method,route}` (histogram), and `http_requests_in_progress{service}` (gauge) — plus a `GET /metrics` route helper (`prometheus_client`'s standard exposition format) each service mounts identically. Default process/GC metrics (`prometheus_client`'s built-in `ProcessCollector`) are included automatically.
- **Domain/business metrics remain owned by each service.** Where a service wants a domain counter (e.g., `anomalies_detected_total`, `recommendations_generated_total`, `business_impact_assessments_total{severity}` — the same metrics ARCHITECTURE.md §10 already anticipates), it imports the shared `Counter`/`Histogram`/`Gauge` factory from `metrics.py` and defines/increments the metric in its own domain code — the shared module never defines a business-named metric itself.
- Database-pool metrics (`db_pool_size`, `db_pool_checked_out`) are exposed via the same shared registry, sourced from the one shared `engine` (`backend/shared/database/database.py`) every service already imports — no per-service duplication.

### 3.6 Tracing Architecture
- `backend/shared/observability/tracing.py` (new shared module): one `init_tracing(service_name)` call, made once in each service's `lifespan()`, that configures the OTel SDK with an OTLP exporter pointed at the `otel-collector`, and applies the standard, off-the-shelf auto-instrumentors: FastAPI (inbound spans), httpx (outbound spans — covers both Gateway's downstream calls and `business_impact_service`'s event delivery, F6), and SQLAlchemy (DB spans, applied to the one shared `engine`).
- No manual span-creation code is required anywhere for the baseline: auto-instrumentation covers "Gateway → downstream service → downstream operation" (including the DB operation) and the independent "`business_impact_service` → `recommendation_service`/`evaluation_service`" event-delivery hop (F6) without any service-specific tracing code.
- Trace context (`traceparent`) propagates automatically via the httpx/FastAPI instrumentors' standard W3C Trace Context header injection/extraction — this is separate from, and complementary to, the `X-Request-ID` correlation header (§3.4), which exists purely for human/log correlation and is not itself a trace-context carrier.
- `gateway_service` and `copilot_service` are instrumented identically to every other service — no bespoke Gateway-routing-aware or Copilot-business-aware tracing logic is added (avoids Phase 12 scope creep, per the non-findings above).

### 3.7 Health Architecture
- **Liveness** (existing, unmodified): `GET /health` on all 9 services — "is the process up and responding," exactly as implemented today. Never changed, never removed. Continues to back every service's own Docker healthcheck and Administration's existing Platform Overview aggregation (Step 7.X A-02) unmodified.
- **Readiness** (new, additive): `GET /health/ready` on the 8 database-backed services (all except `gateway_service`) — calls the existing `check_database_connection()` (`backend/shared/database/health.py`, reused verbatim, not reimplemented) live, per request, returning 200 when the dependency is reachable and 503 otherwise.
- **Dependency health** for `gateway_service` specifically is intentionally *not* a new `/health/ready` route — it already has one, Administration's `/api/v1/administration/overview` (Step 7.X A-02), which fans out to every downstream service's own `/health`. Phase 11 does not duplicate this; Prometheus instead scrapes each service's `/metrics` directly for its own liveness signal (via `up{job=...}`), which is the standard Prometheus-native way to know a scrape target is reachable, without needing gateway_service to proxy it.

### 3.8 Error Visibility Architecture
- 4xx/5xx responses are counted via the shared `http_requests_total{status}` metric (§3.5) — no new component, this falls directly out of the shared HTTP metrics middleware already being added.
- Timeouts and downstream-unavailable conditions (Gateway's existing `DownstreamTimeoutError`/`DownstreamUnavailableError`/`DownstreamServiceError`, `core/errors.py`, unchanged) are logged via the shared structured logger (§3.3) at `ERROR` level with the failing downstream URL and status/exception type (never the raw exception object or response body verbatim, per §3.9) and are visible as failed spans in the corresponding trace (§3.6) — a genuine downstream failure is therefore observable through metrics (a 502/503/504 count), logs (one structured error line, correlated by `request_id`), and traces (a span marked as an error) simultaneously, satisfying §9's "verify the failure becomes observable through logs/metrics/traces."

### 3.9 Grafana Architecture

**Amended at Phase 11 closure (OBS-002, `docs/DECISIONS.md`):** the third dashboard below ("Intelligence Pipeline") required domain metrics that no Phase 11 batch's backend scope ever committed to implementing, and which do not exist anywhere in the repository. Rather than fabricate them, Phase 11 ships two dashboards. Intelligence Pipeline is explicitly deferred to a future initiative that first adds real domain-metric instrumentation to the owning services. See OBS-002 for full rationale.

Two dashboards, each backed entirely by real, live Prometheus/Loki/Tempo data — no dashboard renders a static or seeded number as if it were live telemetry:
1. **Platform Health** — per-service `up`/liveness (from Prometheus scrape health), readiness status (from the `service_readiness` gauge, refreshed on the same cadence as every `/metrics` scrape — added at Phase 11 closure; reuses the existing `check_database_connection()` primitive, no change to `/health` or `/health/ready`'s own contracts), and recent error-rate summary per service.
2. **API & Service Performance** — request rate, latency percentiles (from the `http_request_duration_seconds` histogram), and error rate, sliceable by service/route, plus a panel linking into Tempo traces for slow/error requests.
3. ~~**Intelligence Pipeline**~~ — **DEFERRED (OBS-002).** Would have required service-owned domain metrics from §3.5 (anomalies detected, incidents correlated, recommendations generated, business impact assessments by severity, etc.) that do not exist in this repository as of Phase 11 closure. Building this dashboard is deferred until those metrics are genuinely instrumented by their owning services.

Any dashboard example/seed panel used during Batch 4 development must be clearly labeled (e.g., a provisioning-time annotation or a dashboard explicitly named "Example — not live") and removed or replaced with real-data panels before Batch 4 closes — no seeded number ships in the final `PlatformHealth`/`APIServicePerformance` dashboards.

### 3.10 Frontend Boundary
No new frontend workspace, no Grafana embedding, no frontend-side OpenTelemetry SDK, no user-behavior telemetry. The frontend's existing `X-Request-ID` generation and `ApiError.requestId` surfacing (`frontend/src/app/api/client.ts`, `errors.ts`) already satisfy "correlation information where already appropriate" and "useful error context where genuinely justified" — Phase 11 confirms this continues to correlate correctly once services propagate the same header (§3.4) but adds no new frontend code.

### 3.11 Infrastructure Boundary
Docker Compose only — five new internal-only services (`prometheus`* , `grafana`*, `loki`, `promtail`, `tempo`, `otel-collector` — six, correcting the count) added to the existing `docker-compose.yml`, following the exact same `build`/`image`, `depends_on`, `restart: unless-stopped` conventions already used by every existing service (*Prometheus and Grafana are the only two of these six with a host port mapping). No Kubernetes, Helm, service mesh, mTLS, HA clustering, or multi-region concern is introduced, per §4 of the task.

### 3.12 Telemetry Security Rules
- Never log or trace: passwords, secrets, API keys, access tokens, `Authorization`/session headers, database connection strings/credentials, unrestricted request/response bodies, or raw complaint/customer free-text content beyond what a service already, deliberately surfaces in its own explainability fields (e.g., Root Cause's `explanation`, which is already designed to be human-facing).
- HTTP metrics/traces record method, route template (not raw query strings containing potentially sensitive values), and status only — never full URLs with query parameters, never headers.
- Exception logging records the exception type and a safe message; it never serializes the full exception object, stack-embedded local variables, or an upstream service's raw response body into a log line or span attribute.
- This mirrors the discipline the Gateway's existing error envelope already establishes (`core/errors.py`: "never expose stack traces, SQL errors, raw exception objects") — Phase 11 extends that same discipline to logs, metrics, and traces rather than inventing a new policy.

---

## 4. Batch Plan

### Batch 1 — Observability Foundation
**Purpose:** Establish structured logging, correlation propagation, metrics, and log-shipping infrastructure across all 9 services — no tracing yet.
**Backend:** Rewrite `backend/shared/logging/logger.py` (F2); add `backend/shared/observability/correlation.py` (F3) and wire it into all 9 services' `main.py`, retiring Gateway's private `core/correlation.py`; add `backend/shared/observability/metrics.py` and mount `/metrics` + the HTTP metrics middleware on all 9 services; add `backend/shared/observability/health.py` and mount `/health/ready` on the 8 database-backed services (F4); forward `X-Request-ID` on Gateway's downstream calls and `business_impact_service`'s event-delivery call (F3).
**Frontend:** None.
**Infrastructure:** Add `prometheus`, `loki`, `promtail` to `docker-compose.yml` (internal-only except Prometheus's optional dev port); a static Prometheus scrape config listing all 9 service:port targets.
**Tests/Verification:** Every service's logs are valid JSON with `service`/`timestamp`/`level`/`message` fields; `request_id` is present and identical across a Gateway request and the downstream service log line it produced; `/metrics` returns Prometheus exposition format on all 9 services and Prometheus's own target list shows all 9 as `up`; `/health/ready` returns 200 normally and 503 when Postgres is stopped, on all 8 applicable services; a log line reaches Loki (queried directly) within a few seconds of being emitted.
**Dependencies on previous batches:** None (first batch).

### Batch 2 — Distributed Tracing
**Purpose:** Add distributed tracing across the Gateway-initiated path and the independent event-delivery path.
**Backend:** Add `backend/shared/observability/tracing.py` (§3.6) and call `init_tracing(service_name)` in all 9 services' `lifespan()`; apply the FastAPI/httpx/SQLAlchemy auto-instrumentors.
**Frontend:** None.
**Infrastructure:** Add `otel-collector` and `tempo` to `docker-compose.yml` (both internal-only); Grafana's Tempo datasource is provisioned but dashboards remain Batch 4's concern.
**Tests/Verification:** A representative `GET /api/v1/dashboard` (or any Gateway route) produces one trace spanning Gateway → the downstream service(s) it called → that service's DB query, all as child spans under one trace ID; a representative `BusinessImpactCompleted` delivery produces a second, independent trace `business_impact_service → recommendation_service` (F6); the `request_id` from Batch 1 appears as a span attribute on both.
**Dependencies on previous batches:** Benefits from Batch 1's correlation primitive (to attach `request_id` as a span attribute) but is independently verifiable without it if sequenced differently; sequenced after Batch 1 per the internal architecture's own ordering, which this review confirms is sound.

### Batch 3 — Reliability & Error Visibility
**Purpose:** Make failure conditions genuinely observable; complete the readiness/dependency-health story.
**Backend:** Ensure every Gateway `GatewayError` subclass and every service-level unhandled exception is logged via the shared structured logger at the correct severity with safe context (§3.8); verify `/health/ready`'s 503 path is exercised by the existing downstream-unavailable error paths already in `core/errors.py`; confirm the `http_requests_total{status}` metric correctly buckets 4xx/5xx/timeout responses.
**Frontend:** None beyond confirming the already-existing `ApiError.requestId` (§3.10) continues to correlate correctly — no new frontend code.
**Infrastructure:** None new (uses Batch 1/2's stack).
**Tests/Verification:** Controlled failure scenarios — stop `postgres` (readiness 503 + error log + metric), request a genuinely 404 resource (metric + log, no error-level severity for an expected 404), force a downstream timeout (Gateway's existing `DownstreamTimeoutError` → 504, logged, metered, and visible as an error span) — each confirmed observable through logs, metrics, and traces as applicable.
**Dependencies on previous batches:** Batch 1 (metrics/logging) required; Batch 2 (traces) used where available but not blocking.

### Batch 4 — Grafana + Full Verification
**Purpose:** Ship dashboards against real telemetry and close out Phase 11 with end-to-end verification. **Amended by OBS-002 at closure:** two dashboards (Platform Health, API & Service Performance) shipped; a third ("Intelligence Pipeline") was deferred — see §3.9.
**Backend:** None (consumes Batches 1–3's output only).
**Frontend:** None.
**Infrastructure:** Add `grafana` to `docker-compose.yml` (host port 3001, F1); provision Prometheus/Loki/Tempo datasources and the two shipped dashboards (§3.9, amended by OBS-002) as version-controlled JSON.
**Tests/Verification:** Each of the 2 shipped dashboards renders real, live data (not a seeded/example panel) end to end, confirmed by generating real traffic (a few real API calls) and observing the corresponding panels update; full `docker compose up` brings up all original 9 services plus the 6 new observability services cleanly; documentation/closure updated per the same discipline Step 7.X's own closure used.
**Dependencies on previous batches:** All of Batches 1–3 (dashboards require real metrics, logs, and traces to already exist).

---

## 5. Explicitly Deferred

- **Phase 12 (AI Copilot):** any Copilot-specific tracing/telemetry logic, LangGraph instrumentation, natural-language query observability. `copilot_service` receives only the same generic instrumentation every other service gets.
- **Phase 13 (Production Hardening):** authentication/RBAC on any new observability endpoint or Grafana instance (Grafana ships with its own default admin credential flow for this prototype scope, not integrated with a platform auth system that does not yet exist), production alerting (Alertmanager, PagerDuty-style routing), long-term retention/compaction tuning, multi-region/HA observability.
- **Unnecessary prototype complexity:** Kubernetes/Helm, service mesh, mTLS between services or between services and the observability stack, a dedicated log-aggregation service beyond Promtail→Loki, cloud-managed observability (Datadog/New Relic/CloudWatch), SRE-style runbook automation.
- **Frontend observability workspace or embedded Grafana** — explicitly excluded per §6 of the task; Administration remains the platform's presentation-layer control center and does not gain an observability tab.
- **Redefining `RecommendationStatisticsService` surfacing, Root Cause mutation, full Dashboard filtering, editable Intelligence Configuration, or any other Step 7.X-deferred item** — none of these are Phase 11 concerns and none are pulled forward by this architecture.

---

## 6. Architecture Decisions Recommended for `docs/DECISIONS.md`

Only one genuine architectural decision was identified — everything else in this document is implementation detail flowing from already-established principles (shared-code-as-primitives-only, Gateway/BFF boundary, no-fabrication):

- **OBS-001 — Correlation ID Propagation Becomes a Shared, Cross-Service Primitive.** Context: correlation IDs existed only at the Gateway edge (F3) and were never forwarded downstream, which Phase 11's structured-logging goal cannot satisfy as-is. Decision: generalize Gateway's existing `X-Request-ID` middleware into a shared module every service installs, and forward the header on every outbound service-to-service call (Gateway's downstream calls and `business_impact_service`'s event delivery). This is worth recording because it changes an existing, previously Gateway-only architectural component (`core/correlation.py`) into a cross-cutting shared one, and establishes that inter-service HTTP calls must now carry this header going forward — a real, durable convention future services must follow, not merely an implementation detail of one dashboard or endpoint.

No ADR is recommended for: the choice of Prometheus/Grafana/Loki/Tempo/OTel (already named in ARCHITECTURE.md §10 as the anticipated stack — confirming, not deciding); the Promtail log-shipping mechanism (F5, a mechanism selection grounded in the existing Docker `json-file` default, not a new architectural principle); the `/health` vs. `/health/ready` split (a direct, additive application of an already-standard liveness/readiness pattern, not a new decision); or the Grafana port remap (F1, a configuration detail).

---

## 7. Definition of Done

Phase 11 is complete only when:

1. All 9 backend services emit structured JSON logs (service, timestamp, level, message, request_id-when-present) to stdout, shipped to Loki via Promtail with no service-level networking dependency added.
2. `X-Request-ID` is generated/reused at the Gateway (and independently at every service, for requests that don't originate there) and is forwarded on every inter-service HTTP call, verified present and identical across at least one real Gateway→downstream→log chain.
3. All 9 services expose `/metrics` in Prometheus exposition format, scraped successfully (`up == 1` for all 9 in Prometheus's own target list), including the shared HTTP request-count/latency/in-progress metrics plus at least the domain metrics already named in ARCHITECTURE.md §10 that a given service can meaningfully own.
4. Distributed tracing captures, end to end, at least two representative real flows: a Gateway-initiated request through a downstream service and its database operation, and the independent `business_impact_service → recommendation_service`/`evaluation_service` event-delivery hop — both visible as a single connected trace each in Tempo/Grafana.
5. Liveness (`/health`, unmodified) and readiness (`/health/ready`, new, dependency-checked) are both real and distinguishable on every service where the distinction is meaningful (8 of 9 — all except `gateway_service`).
6. A representative 4xx, 5xx, timeout, and downstream-unavailable scenario are each demonstrated observable through logs, metrics, and (where applicable) traces, without any fabricated/static number standing in for live data.
7. **Amended (OBS-002):** Grafana ships the two dashboards backed by telemetry that exists as of Phase 11 — Platform Health, API & Service Performance — each rendering real, live telemetry only, verified by generating real traffic and observing panels update. Intelligence Pipeline is explicitly deferred pending real domain-metric instrumentation in a future initiative; it does not block Phase 11 closure.
8. No telemetry surface (log, metric, span, dashboard) exposes any item listed in §3.12.
9. Full existing verification suite (backend pytest, frontend Vitest, typecheck, lint, production build, `docker compose config`) remains green with the six new observability services added — no regression to any Phase 1–10/Step 7.X capability.
10. No Phase 12 or Phase 13 capability was introduced (verified by an explicit closure-time check against §5 of this document, mirroring Step 7.X's own closure discipline).
