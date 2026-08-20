
# CHANGELOG

All notable engineering changes to the Customer Experience Intelligence & Failure Detection Platform are documented in this file.

The format follows a simplified version of the Keep a Changelog convention.

---

# 2026-08-17 (Dataset/DatasetVersion domain model — multi-dataset isolation and versioning)

## Dataset identity, versioning, extend/re-analyze lifecycle, dataset-scoped Dashboard/Analytics, dataset-scoped detection/investigation/recommendation pipeline

Before this change the platform had no concept of a dataset: every complaint, real or seeded, lived in one global table, and every downstream query scanned it unconditionally. This closes that gap end-to-end — schema, six backend services, the Gateway orchestrator, and the Data workspace. Full decision record: `docs/DECISIONS.md` (AD-12).

### Added

- **`Dataset`/`DatasetVersion` tables** (`ingestion_service`) — a dataset is a persistent analytical workspace; a version is a finalized snapshot marker (record counts, pipeline status), never a data partition. `Complaint` gains `dataset_id` and `dataset_version_id` real FKs. Every pre-existing row is backfilled into one deterministic "Legacy / Demo Data" dataset (`backend/shared/constants/seed_ids.py`) — `dataset_id` is `NOT NULL` everywhere from the start, no nullable escape hatch.
- **`dataset_id` scoping across `anomaly_service`, `root_cause_service`, `business_impact_service`, `recommendation_service`** — every detector, aggregator, repository, and API route now requires a `dataset_id`. `ActiveAnomaly.fingerprint` uniqueness changes from global to `(fingerprint, dataset_id)`, so two unrelated datasets can share a fingerprint without colliding.
- **`gateway_service/app/services/dataset_analysis_orchestrator.py`** — the real pipeline behind `POST /api/v1/datasets/{id}/versions/finalize`: closes the draft version, then synchronously runs enrichment → anomaly detection → incident correlation → per-incident root-cause and business-impact analysis, before returning the version's terminal status. No task queue was added; this is a disclosed, deliberate scale limitation.
- **Gateway dataset API surface** — `POST/GET /datasets`, `GET /datasets/{id}[/versions[/{versionId}]]`, `POST /datasets/{id}/versions/finalize`, `POST/GET /datasets/{id}/complaints`. `GET /dashboard` and `GET /analytics/trends` now require `datasetId` — there is no "all datasets" fallback; a request with no scope is rejected, not silently served globally.
- **Data workspace rebuilt** (`frontend/src/workspaces/ingestion`) around dataset identity: a dataset list/create view when nothing is selected, and a dataset detail view (version banner, Upload → Preview → Confirm → Ingest, an explicit "Finalize & Analyze" action, real version history) when one is. `DatasetProvider` (`frontend/src/app/context/DatasetContext.tsx`) holds the app-wide `selectedDatasetId`/`selectedDatasetName` in `localStorage`, mounted in `AppProviders` — every dataset-aware workspace reads from it, and none falls back to a global query.
- **Dashboard and Analytics are dataset-scoped** — both hooks fetch nothing while no dataset is selected and both workspaces render an explicit "No dataset selected" empty state with a link to Data, rather than an empty chart or a silently-global request. Both show a context banner naming the active dataset.
- **Enum-casing normalizer** (`frontend/src/shared/constants/enums.ts`, used by `parseComplaintRows.ts`) — a hand-synced TS mirror of the backend's five real closed enums (`SourceChannel`, `CustomerSegment`, `CustomerType`, `OperationalArea`, `ServiceType`). Uploaded rows are normalized (casing, spaces/hyphens → underscores) and validated client-side against the real allow-list before submission, so a casing mismatch is caught as a per-row preview error instead of surfacing as a 422 after the request is sent.

### Fixed

- **Two divergent Alembic migration heads.** The dataset migration chain's first revision (`a1c3d5e7f902`) was authored against a stale `down_revision` (`f05ea2afc3ee`), which had already grown a sibling chain (gateway identity tables, Copilot ownership, recommendation decision attribution) by the time it was written. Left as committed, `alembic upgrade head` would have failed outright with "Multiple head revisions are present" against any real database. Rebased onto the actual head (`e35a123597e1`); confirmed with `alembic heads` (now one) and a full `alembic upgrade head` from an empty database.
- **A real `CREATE TYPE ... AS ENUM` double-creation and an unbound `sa.func.now()` bind parameter**, both in the same migration, found only by actually running it against a live, empty PostgreSQL database (never caught by the static migration-graph check or by any test, since the backend test suite runs against SQLite-free in-memory fixtures, not this migration). Fixed by letting `CREATE TABLE`'s own enum column create the type once (removing the redundant explicit `.create()` call) and by omitting `inserted_at` from two `bulk_insert` calls so the column's own `server_default=now()` applies, instead of binding an unevaluated SQL-expression object as a literal asyncpg parameter.

### Verified

- Backend: `PYTHONPATH=. python -m pytest backend -q` — **1232 passed, 21 failed, 161 skipped**. The 21 failures are the pre-existing baseline (`test_auth_api.py`, `test_event_isolation.py`, `test_main.py`, `test_rbac_api.py` — all require a locally-reachable PostgreSQL this sandbox doesn't have); identical file/test list before and after this change.
- Frontend: `npx tsc -b --noEmit`, `npm run lint`, `npm run build` all clean; `npx vitest run` — **366 passed / 366, 51 files, 0 failed**.
- Migrations: `alembic upgrade head` from an empty, isolated PostgreSQL container (via `docker compose`) — full chain applies cleanly, single head, real schema verified by direct query (`datasets`/`dataset_versions` tables, `complaints.dataset_id`/`dataset_version_id` FKs, legacy backfill row present). `alembic downgrade` back through all five new revisions and `upgrade head` again both succeed cleanly.
- End-to-end (real running services, not mocked): created two unrelated datasets, ingested and finalized both, confirmed zero cross-dataset contamination in Analytics/Dashboard, extended the first dataset with 6 more records, confirmed a new version (cumulative 18, new 6) was created while version 1 (12 records) remained independently queryable, confirmed the Dashboard/Investigations/Analytics routes reflect the post-extension cumulative re-analysis, and confirmed real conflict/validation states (`409` duplicate, `404` unknown dataset, `422` missing required `datasetId`, `400` invalid enum casing).

### Known regression, not fixed in this pass

- **Copilot's `analytics_trends` tool is now always broken.** `anomaly_service`'s `/trends*` routes started requiring `dataset_id` as part of this feature; `copilot_service/app/services/analytics_tool.py` was never updated to supply one, so every call now returns a real `422` that the tool correctly converts into an honest `found: false` error (no crash, no fabricated data) — but the capability itself is gone. Fixing it means adding a dataset field to `WorkspaceContext`, which Phase 12's architecture document states is a frozen, `extra="forbid"` five-field contract — a genuinely architectural change requiring explicit sign-off, not something to change unilaterally under this pass. Copilot's other tools (investigation, root-cause, recommendation, business-impact) remain functional — they resolve by `incident_id`, and those routes were deliberately left dataset-independent (see AD-12 decision 12).

### Decided, not built

- **No dataset version comparison** — diffing two versions' record sets or derived intelligence against each other. Explicitly requested in the originating brief and explicitly deferred, confirmed with the user before implementation.
- **No report generation/export** — no backend capability exists for this anywhere in the platform; none was added.
- **No live version/status badge in Dashboard's or Analytics' dataset-context banner** — only the dataset name (captured at selection time) is shown there, to avoid a second network request per workspace on every load; live pipeline/version status remains the Data workspace's responsibility alone.
- **`evaluation_service` still has no `dataset_id`** on its own persistence or event payload — it is not Gateway-exposed and extending it was out of scope for this pass, same as the pre-existing, already-disclosed gap.

> Not verified: no browser automation was available for this pass. The eight end-to-end user-journey scenarios in the originating brief (new dataset → isolated analysis → extend → new version → historical access, contamination check) were exercised via direct Gateway HTTP calls where the sandbox allowed it; see the session's final report for the exact pass/fail/not-verified breakdown per scenario.

---

# 2026-08-17 (Product experience reconstruction — ingestion, root-cause actions, Administration labeling)

## Data / Ingestion workspace, root-cause lifecycle actions, Administration capability badge, shared design-system primitives

A full reconciliation of documented product intent against actual backend capability and actual frontend exposure (three independent explorations: docs, frontend, backend). Most apparent gaps (Analytics' placeholders, Copilot's no-LLM state, four of Administration's six sections) were confirmed as already honest, deliberate decisions (AD-9, AD-10), not defects, and were left untouched. Four verified, real gaps were closed. Full decision record: `docs/DECISIONS.md` (AD-11).

### Added

- **Gateway ingestion exposure.** `gateway_service/app/api/ingestion.py` + `services/ingestion_proxy.py` proxy `ingestion_service`'s real `POST/GET /complaints` (previously implemented, never Gateway-mounted) as `POST /api/v1/ingestion/complaints` (`operator`) and `GET /api/v1/ingestion/complaints[/{id}]` (`viewer`). New `gateway_service/tests/test_ingestion.py`.
- **Data workspace** (`frontend/src/workspaces/ingestion`, route `/data`, first item in primary navigation) — the platform's entry point into the operational intelligence lifecycle. Upload a CSV/JSON file or add a complaint manually; rows are parsed and validated client-side, previewed, confirmed, then submitted one real request at a time with a real per-row success/duplicate/failed outcome; a "Recently ingested" section reads back what has actually persisted (`GET /api/v1/ingestion/complaints`).
- **Root-cause lifecycle actions, Gateway-exposed.** `root_cause_service`'s real `confirm`/`reject`/`refresh` routes are now proxied (`PATCH/POST /api/v1/investigations/{incidentId}/root-cause/{confirm,reject,refresh}`, resolving the incident's RootCause id server-side), including translating the service's real 409 (invalid lifecycle transition) into the Gateway's own `ConflictError` rather than a generic 502 (new `patch_resource` helper in `core/downstream.py`). `RootCauseExplanationDTO` now carries the real `status` field it previously dropped. Investigations' Root Cause Analysis section renders real, `operator`-gated Confirm/Reject/Re-run controls and a status Badge.
- **`ingestion_service`'s first automated test suite** (`tests/test_api_complaints.py`) — previously empty, unlike every sibling service.
- **`AdministrationStatusBadge`** — a "Real data" / "Not yet operational" indicator next to each of Administration's six section titles, making the real/illustrative split each section's own `AdvisoryNotice` already discloses in prose scannable at a glance. Wording deliberately avoids "live"/"real-time"/"monitoring" (ADM-004).
- **Shared design-system primitives** (`frontend/src/shared/components/primitives`): `Button`, `Card` (built on the existing `Panel`), `DataTable`, and `Modal` (the platform's first true blocking dialog, giving `--color-scrim` its first real consumer). Used by all new work in this pass and one flagship retrofit (`ConnectedSystemCard`). The remaining ~14 hand-rolled workspace cards are an explicitly recorded, not-yet-migrated gap — not silently done, not silently ignored.

### Verified

- Backend: `python -m pytest backend -q` — **1221 passed, 21 failed, 161 skipped**. Every failure is in `test_auth_api.py`, `test_event_isolation.py`, `test_main.py`, and `test_rbac_api.py` — all use a real `TestClient(app)` lifespan requiring a locally-reachable PostgreSQL, unavailable in this environment; none touches ingestion, investigations, or root-cause code. Every new/changed test (`test_ingestion.py`, the extended `test_investigations.py` and `test_rbac_api.py` role-gating cases, `ingestion_service/tests/test_api_complaints.py`) passes standalone without a database.
- Frontend: `npm run typecheck`, `npm run lint`, `npm run build` all clean; `npm test` — **366 passed / 366, 51 files, 0 failed** (two pre-existing tests updated for real, intended changes: the primary-navigation id list now includes `ingestion`; Administration's "never says live" assertion still holds against the new badge's actual wording).
- Gateway route table inspected directly (`app.routes`): all three new root-cause action routes and all three new ingestion routes present at their intended paths.

### Decided, not built

- **No bulk/CSV backend ingestion endpoint** — the Data workspace parses a file client-side and submits each row as a separate real request against the existing single-record endpoint; a genuine server-side bulk-import capability was not added.
- **No repository-wide Button/Card migration** — new primitives are additive; ~14 existing hand-rolled cards are left as-is (cosmetic churn, real regression risk, no functional gain).
- **No changes to Analytics, Copilot's LLM configuration, or Administration's four illustrative sections' underlying data** — all already honestly presented; out of scope for this pass by design.

> Not verified: no browser automation was available for this pass. Rendered appearance, CSS layout, real click-through interaction (including the new Data workspace's upload/preview/confirm flow and the Modal's focus-trap behavior), and behaviour at actual viewport sizes remain for a manual walkthrough.

---

# 2026-08-16 (Final frontend / product-experience pass)

## Session expiry handling, Analytics visualization, illustrative-content disclosure, role-aware UX

A final audit of every frontend surface against the capability actually behind it. Full decision record for the two product decisions: `docs/DECISIONS.md` (AD-10).

### Added

- **Analytics charts, drawn from the real trend response.** `GET /api/v1/analytics/trends` returns five populated numeric series; the view model previously reduced them to a handful of sentences and discarded the rest. It now carries the arrays through unchanged, and `TrendVisualization` renders five charts, each mapped 1:1 to one array: complaint volume per day, average sentiment score per day, and complaints by category, region, and urgency. Nothing is smoothed, forecast, ranked, or re-bucketed; a series the backend returned empty draws no chart rather than an empty axis.
- **Two chart primitives, no new dependency** — `TimeSeriesChart` (single-series line/area) and `CategoryBarChart` (horizontal bars), plus `ChartFrame`, built from inline SVG and the existing CSS tokens. Every chart ships an equivalent data table ("View as data"), a `role="img"` accessible name, and a per-mark hover value, so a charted number is never encoded only as geometry. New `--color-chart-*` tokens are defined for light and both dark paths.
- **`AdvisoryNotice`** — one shared feedback component for stating a fact *about* content that is rendering correctly, distinct from `ErrorBoundary` (failed), `EmptyState` (nothing to show), `FutureCapabilityPlaceholder` (not computed yet), and `PartialFailureNotice` (partially degraded response).
- **`describeApiError`** — one shared status→sentence mapping for `0`/`401`/`403`/`404`/`400`/`422`/`5xx`, replacing the partial per-surface copies. A `403` now names the user's role as the reason; a `5xx` envelope is never surfaced raw.
- **`AuthContext.hasRole` and `useOptionalAuth`** — a role check mirroring the Gateway's own hierarchy (`admin` satisfies `operator` satisfies `viewer`), and a provider-tolerant context read for components that render fine without session information.

### Fixed

- **A session that expired mid-use left the user stranded.** `AuthContext` learned about authentication exactly once, at bootstrap. The session cookie has a finite `Max-Age` (1800s in development), so an expiry produced a `401` on every subsequent workspace fetch, which each workspace surfaced as a generic "Something went wrong loading …" — the user was never told their session had ended, was never returned to `/login`, and could only recover by reloading. One root cause with five identical symptoms, fixed once: the API client now emits a single centralized 401 signal (`app/api/unauthorized.ts`), `AuthContext` consumes it and transitions to signed-out, `RequireAuth` redirects, and the login page explains why. A deliberate sign-out is not labelled an expiry, and a rejected password never is.
- **Four Administration sections presented fabricated content as real.** User & Access Management, Data Sources & Integrations, Platform Governance, and Audit & Change History are presentation-only — a documented limitation, but one stated *only in source comments*. A user saw specific user counts, a list of external systems marked "Connected", a 24-month retention policy, and an audit ledger naming individual people at precise timestamps, with nothing indicating none of it was real. Two entries also described capabilities the platform does not have: both claimed single sign-on, where the platform authenticates with email and password. Each section now renders a visible disclosure naming what is illustrative and what the platform actually does. The two sections with real backend data (Platform Overview, Intelligence Configuration) are unchanged.
- **The two operator-gated actions were discoverable only by failing.** A `viewer` saw a fully-enabled decision form and Copilot composer, and learned the restriction only after composing a request and receiving a `403`. Both now state the role requirement up front. Neither control is hidden: the Gateway remains the authorization boundary, and hiding a control would misrepresent why it is unavailable.
- **A placeholder chart affordance that had never drawn anything.** `TrendNarrativeCard` rendered a small dashed box containing a static `trendUp` icon, captioned in code as a "reserved chart area". Removed, now that real charts exist.

### Verified

- Full frontend suite: **366 passed / 366, 51 files, 0 failed** (`--maxWorkers=2`), up from 339/49 — 27 new assertions covering session expiry, the role hierarchy, the role-restriction notices, the shared error wording, the Administration disclosures, and the chart layer. `npm run lint`, `npm run typecheck`, `npm run build` all clean.
- Through the frontend's own origin and proxy (`http://localhost:3000/api/...`) against the running dev stack with real session cookies: all ten frontend-called endpoints `200`; `viewer` reads `200` and both operator-gated writes `403`; `admin` writes `200`; anonymous `401`; an invalid `period` `400`; an unknown incident `404`. Copilot's honest "no LLM configured" disclosure re-confirmed unchanged.
- Every new module confirmed compiling and served by the containerized Vite dev server.

### Decided, not built

- **Data ingestion has no frontend workflow.** `ingestion_service`'s `POST /complaints` is real but is not Gateway-exposed and is not host-published, so a browser cannot reach it; adding a Gateway route would be new backend capability, not a frontend fix (see AD-10, consistent with AD-9's reasoning). Data continues to enter through the operator-run seed tooling and direct in-network API calls, and Administration now says so on the page.

> Not verified: no browser automation was available for this pass. Rendered appearance, CSS layout, real click-through interaction, and behaviour at actual viewport sizes remain for a manual walkthrough.

---

# 2026-08-16 (Post-closure correction pass — RC1–RC4)

## Frontend API path contract, navigation, router error surface, seed tooling

Four defects found by the first genuine end-to-end walkthrough of the running application. All four are user-facing; none were reachable by the existing test suite, because every frontend test asserted the same wrong path the source code used, and the F05/F06 backend validation exercised the Gateway directly rather than through the frontend's own API modules.

### Fixed

- **Every workspace API call 404'd (RC1).** `apiClient`'s base URL is `/api`, and the Gateway mounts its routers at `/api/v1/...`, but five workspace API modules issued bare paths (`/dashboard`, `/analytics/trends`, `/administration/overview`, `/administration/intelligence-configuration`, `/recommendations/{id}`, `/recommendations/{id}/decision`, `/investigations/{incidentId}`). `authApi.ts` and `copilotApi.ts` were already correct, which is why login and Copilot worked while every workspace showed an error state. Path string literals corrected to `/v1/...`; no method, hook, type, or response-handling change.
- **Primary navigation linked to routes that do not exist (RC2).** `PRIMARY_NAVIGATION` listed Investigations and Recommendations at the bare `/investigations` and `/recommendations` paths, but the router only ever defined the parameterized detail routes (`/investigations/:incidentId`, `/recommendations/:recommendationId`) — clicking either sidebar entry produced a router error. Both entries removed; the sidebar is now Dashboard, Analytics, Administration. The detail routes, drill-down helpers, and both workspaces are untouched and still reachable from the Dashboard.
- **No not-found or router-error surface (RC3).** Any unmatched URL fell through to react-router's raw "Unexpected Application Error!" developer screen. Added `RouteErrorView` (built from the existing `EmptyState` foundation — no new UI primitive, no new dependency), wired as the authenticated root route's `errorElement` and as a `path: '*'` catch-all child so it renders inside `AppShell` with the sidebar intact.
- **The documented sample-data command had never worked (RC4).** `load_sample_complaints.py` resolved only a fixed in-repository path, which is absent from the backend image because `.dockerignore` deliberately excludes `datasets/`. Added an optional `--file` argument; the no-argument default path resolution is unchanged. README now documents the real two-step `docker cp` + `--file` workflow.

### Verified

- Full frontend suite green: 337 → 339 passed, 49 files (two new assertions covering the navigation contract and the not-found surface). `npm run lint`, `npm run typecheck`, and `npm run build` all clean.
- Through the running Gateway with a real session cookie: `GET /api/v1/auth/me`, `/v1/dashboard`, `/v1/analytics/trends`, `/v1/administration/overview`, `/v1/administration/intelligence-configuration`, `/v1/investigations/{id}`, `/v1/recommendations/{id}` all `200`; the previously-used bare paths confirmed `404`, which is the defect itself reproduced.
- Sample-data seeding executed end-to-end via `docker cp` + `--file`: 8 records processed, 8 inserted, 0 errors. The no-argument invocation still reports the unchanged default path.

---

# 2026-08-16 (Phase 13 closure)

## Phase 13 – Production Hardening

Gateway-owned identity, authentication, RBAC, internal service trust, recommendation decision attribution, Copilot conversation ownership, database backup/restore, investigation aggregator concurrency, Docker dev/production-like hardening, and CI — delivered across eleven implementation batches, followed by a whole-project audit and two closure-blocking corrections. Full detail: `docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md`; full decision record: `docs/DECISIONS.md` (AD-1 through AD-8).

### Added

- **Identity & authentication** — `users`/`roles`/`user_roles` (gateway-owned), bcrypt password hashing, JWT session in an `HttpOnly`/`SameSite=Lax` cookie, `login`/`logout`/`me`.
- **RBAC** — `viewer`/`operator`/`admin`, enforced on all 12 Gateway routes; 401-before-403 ordering structurally guaranteed.
- **Internal service trust** — `X-Internal-Secret` on the two genuine internal mutation routes; Gateway-attested principal propagation for recommendation decisions and Copilot conversations.
- **Recommendation decision attribution** — `decided_by` (never client-supplied) + an append-only `recommendation_decision_history` table, written atomically with the current-state update.
- **Copilot ownership** — `owner_id` on conversations, owner-only access and deletion.
- **Database backup/restore** — real `pg_dump`/`pg_restore` round-trip tooling with isolated-container restore verification.
- **Docker hardening** — `docker-compose.prod.yml`: multi-stage nginx-served frontend, no source bind mounts, network segmentation, non-root containers, PostgreSQL not host-published.
- **CI** — GitHub Actions: backend tests against a real Postgres service container, frontend lint/typecheck/test/build, Compose config validation.
- **First-user bootstrap** — a controlled, idempotent, operator-invoked script (`backend/tooling/seed_data/bootstrap_admin_user.py`); no public registration endpoint exists.

### Fixed

- A fresh-database Alembic migration failure (`f05ea2afc3ee`'s Postgres enum type was never created before use) that blocked `alembic upgrade head` on any genuinely empty database, and consequently CI's first run. Fixed in place after a first attempted fix (a corrective migration positioned after the failing one) was proven, with direct runtime evidence, unable to work — Alembic aborts the whole chain at the first failing migration, so a later migration is never reached. See `docs/DECISIONS.md` AD-7 for the full analysis.

### Verified

- Full backend suite green (1,220+ passed, 0 failed) on a database migrated end-to-end from empty; full frontend suite green (337 passed, 48 files).
- Real login → `/auth/me` → protected-route → logout → protected-route round trip through a running Gateway, using a bootstrap-created user.
- Backup/restore round-trip verified with Phase 13's identity and attribution tables present.

### Known Limitations Carried Forward

No real LLM provider is configured (Copilot's fallback behavior is real and tested, never live-model reasoning); root-cause confirm/reject/refresh exists at the service layer but is not yet Gateway-exposed; the frontend does not yet hide controls a user's role can't use (the backend RBAC boundary is authoritative regardless); `evaluation_service`'s output is not yet surfaced anywhere; `ingestion_service` has no dedicated test suite; a twelve-stage, saved synthetic-data validation report has not yet been produced.

---

# 2026-08-14 (Phase 12 closure)

## Phase 12 – AI Copilot (Batches 1–6, Final Closure)

Phase 12 delivered a read-only, evidence-grounded AI Copilot: natural-language interpretation over intelligence the platform already produces, never new domain intelligence. Delivered across six implementation batches plus this closure pass. Full detail and the complete Definition-of-Done table: `docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md` §36.

### Added

- **Copilot API foundation (Batch 1)** — `copilot_service` (internal-only) and a new Gateway-routed `/api/v1/copilot/*` surface; the frozen `CopilotResponse` contract (`answer`/`keyFindings`/`evidenceReferences`/`relatedEntities`/`visualizationHint`/`limitations`/`conversationId`/`requestId`), camelCase (Gateway) and snake_case (`copilot_service`) kept strictly separate.
- **Read-only tool registry (Batch 2)** — seven tools (Recommendation, Recommendation Decision Status, Root Cause, Business Impact, Investigation, Analytics/Trend, Administration/Configuration Read), each calling real domain services directly, never the public Gateway; every known mutation endpoint on every domain service explicitly, individually excluded (`docs/DECISIONS.md`, COPILOT-001).
- **LLM orchestration (Batch 3)** — a provider-agnostic LLM adapter (`NullLLMProvider` honest default; `OpenAICompatibleProvider` opt-in), a bounded (≤3-round) LangGraph orchestration graph, a layered prompt architecture with prompt-injection resistance, and evidence-grounded synthesis — a claimed-but-fake evidence id is always dropped before reaching a response.
- **Conversation persistence (Batch 4)** — `copilot_conversations`/`copilot_messages`, owned entirely by `copilot_service` on the platform's existing shared PostgreSQL instance (`docs/DECISIONS.md`, COPILOT-002); deterministic message ordering, bounded conversation history fed back into the prompt, and no automatic retention (a deliberate, documented prototype choice, not an oversight).
- **Frontend Copilot experience (Batch 5)** — a floating, non-full-screen launcher/panel mounted once in `AppShell.tsx`; consumes the real Gateway API only; renders evidence, related entities, limitations, and a safely-mapped `visualizationHint` (never executable model output, never a fabricated chart); retains and reuses the backend-issued `conversationId` across turns.
- **Evaluation harness (Batch 6)** — a `copilot_service`-owned agent-evaluation harness (`app/evaluation/`) covering all nine architecture-defined measures (tool selection, answer grounding, citation correctness, hallucination, conflict handling, unsupported-request handling, scope preservation, safety/read-only, completeness); a deterministic, versioned dataset of clearly-labeled synthetic fixtures; runs through the real orchestration/persistence path, never a second implementation; strictly independent of the Phase 8 `evaluation_service` (verified by AST-level import checks in both directions).

### Verified

- Full backend suite green (1203 passed) at closure; frontend suite green (321 passed) as of Batch 5, unchanged since (no frontend file touched by Batch 6).
- Real running-service evidence throughout: a real two-turn Copilot conversation through the actual Gateway → `copilot_service` → PostgreSQL path; a real browser session showing the panel open without covering the workspace; the evaluation harness run live inside the real `copilot_service` container, 8/8 cases passing, including genuine (non-fixture) evidence grounding against a live `anomaly_service` trend query.
- Gateway's 7 pre-existing public routes/5 aggregators confirmed byte-for-byte unchanged (`git diff` across the full Phase 12 commit range).
- No mutation capability reachable from any Copilot tool, verified structurally (no mutating HTTP verb helper exists anywhere in `copilot_service`'s domain-facing code) and via a live evaluation-harness case that scripted a mutation-shaped tool name and confirmed the real tool registry rejected it without executing anything.

### Known Limitations (documented, not fabricated)

- No real LLM provider is configured in this environment; every verification used the honest `NullLLMProvider` fallback or, for evaluation cases, a deterministic scripted stand-in — never real model reasoning.
- Copilot's launch context never includes `filters`/`timeRange` (mounted outside every workspace's own React Context provider tree; both fields are optional on the frozen contract).
- No tool-running state distinct from generic loading exists in the frontend — the frozen backend contract has no streaming signal to honestly drive one.
- Two pre-existing, unrelated issues remain untouched: `business_impact_service`'s missing `httpx` direct dependency; the pre-Phase-12 recommendation-decision migration's enum-creation bug. The frontend's pre-existing base-path mismatch remains present in every workspace other than Copilot's own module.

### Explicitly Deferred

Production retention/TTL for conversation data, authentication/RBAC (Phase 13), a public evaluation UI or Gateway evaluation endpoint, and the platform's long-term "Organizational Knowledge" vision (ARB-002/ARB-005) — see `ROADMAP.md` and `docs/DECISIONS.md`.

---

# 2026-08-13 (Phase 11 closure)

## Phase 11 – Observability & Reliability (Batches 1–4, Final Closure)

Phase 11 delivered structured logging, request correlation, HTTP metrics, distributed tracing, reliability/error visibility, and a Grafana operational visualization layer across all 9 backend services, closed out by a final architecture-reconciliation review. Delivered across four implementation batches plus this closure pass, which resolved two contradictions Batch 4 identified between the frozen architecture and repository reality before Phase 11 could be declared complete.

### Added

- **Logging & correlation (Batch 1)** — structured JSON logging (`backend/shared/logging/logger.py`) on all 9 services, shipped to Loki via Promtail; `X-Request-ID` correlation generated/reused at every service and forwarded on every inter-service call (`backend/shared/observability/correlation.py`).
- **Metrics (Batch 1)** — `http_requests_total`/`http_request_duration_seconds`/`http_requests_in_progress` on all 9 services (`backend/shared/observability/metrics.py`), scraped by Prometheus; `/health` (liveness) and `/health/ready` (readiness, 8 DB-backed services) both real and distinguishable.
- **Distributed tracing (Batch 2)** — OpenTelemetry auto-instrumentation (FastAPI/httpx/SQLAlchemy) on all 9 services, exporting via an OTel Collector to Tempo; W3C trace-context propagation end to end.
- **Reliability & error visibility (Batch 3)** — every `GatewayError` now logged at status-appropriate severity (client 4xx at `INFO`, server 5xx at `ERROR`); unhandled exceptions on all 9 services now logged via a shared handler (`backend/shared/observability/error_logging.py`) with the original response contract unchanged; a raw-response-body telemetry-safety leak in `business_impact_service`'s event publisher fixed.
- **Grafana (Batch 4 + closure)** — `grafana` service added to `docker-compose.yml` (host port `3001`, frontend unaffected on `3000`), file-provisioned Prometheus/Loki/Tempo datasources, and two dashboards: **Platform Health** and **API & Service Performance** (`infrastructure/observability/grafana/`).
- **`service_readiness` Prometheus gauge (closure)** — one bounded gauge (`service` label only) added to `backend/shared/observability/health.py`, refreshed on the same cadence as each service's own `/metrics` scrape (no new scrape target, no change to `/health`/`/health/ready`'s response contracts); backs Platform Health's new readiness panel.

### Verified

- Full backend suite green (972 passed, 41 pre-existing skips, 0 failures); frontend typecheck/lint/build green; one frontend test (`AdministrationIntegration.test.tsx`) confirmed pre-existing/flaky (fails only under full-suite load, passes 6/6 isolated, zero frontend files touched by Phase 11).
- Real running-service evidence (not configuration-only): a genuine Postgres outage produced a real `503` from `/health/ready` and a real `service_readiness` drop to `0`, recovering after Postgres returned; a genuine downstream-unavailable failure (`recommendation_service` stopped) produced a real `503`, visible simultaneously in Prometheus, Loki, and Tempo; real traces observed end to end (Gateway → downstream service → DB).
- Both shipped Grafana dashboards confirmed rendering real, live telemetry via direct query execution through Grafana's own datasource proxy.

### Architecture Amendment

- **OBS-002** (`docs/DECISIONS.md`): the originally-specified third dashboard, "Intelligence Pipeline," required service-owned domain metrics (anomalies detected, recommendations generated, etc.) that were never implemented in any Phase 11 batch and do not exist anywhere in the repository. Rather than fabricate them, Phase 11 ships two dashboards; Intelligence Pipeline is deferred to a future initiative that first adds real domain-metric instrumentation. `docs/architecture/phase-11/PHASE_11_ARCHITECTURE.md` §3.9 and its Definition of Done (§7, item 7) amended accordingly.

### Known Limitation (documented, not fabricated)

- The API & Service Performance dashboard's "Recent Slow/Errored Traces" Tempo panel uses a valid TraceQL query, and Tempo genuinely contains matching traces (verified directly and via Grafana's raw proxy), but executing it through Grafana's own dashboard query engine fails with "unsupported query type" — reproduced identically on `grafana:10.4.2` and `grafana:11.3.0`, ruling out a simple version gap. Root cause undetermined after extensive testing; left as an open, disclosed limitation.

### Explicitly Deferred

Intelligence Pipeline dashboard and its underlying domain metrics; `business_impact_service → recommendation_service/evaluation_service` event-delivery trace re-verification (evidence reused from Batch 2, unchanged). Production alerting, SLO/SLI management, authentication/RBAC on any observability endpoint, mTLS/service mesh, Kubernetes/Helm, and HA/multi-region remain out of scope for Phase 11 — see `ROADMAP.md` and `docs/DECISIONS.md`.

---

# 2026-08-13

## Phase 10 – Step 7.X (Intermediate Capability Completion)

Step 7.X closed a bounded, audited set of gaps left after Phase 10 Step 7: real backend data that existed but was unwired, small honestly-missing capabilities, UX-honesty corrections where illustrative content was presented with the same visual confidence as real data, and two capabilities that required an explicit architectural decision before implementation. Scoped and designed by a dedicated three-document audit trail (`docs/architecture/phase-10/STEP_7X_CAPABILITY_GAP_INVENTORY.md`, `STEP_7X_SCOPE_FREEZE.md`, `STEP_7X_IMPLEMENTATION_ARCHITECTURE.md`), delivered across six implementation batches and this closing verification/cleanup batch. This step does not begin, and is not a substitute for, Phase 11.

### Added

- **Dashboard evidence & honesty** — Supporting Evidence now renders real category/region/sentiment/urgency trend summaries from `anomaly_service` (previously hardcoded); the Gateway's partial-failure `warnings` signal is now surfaced on both Dashboard and Investigation; Recommended Focus's structural always-empty state is resolved; Dashboard's four scope-filter context setters are now symmetric.
- **Investigation intelligence** — Business Impact now carries its own confidence classification (`business_impact_service/app/domain/confidence.py`), structurally independent from Root Cause's per ARB-008 (different module, different band thresholds, never shared); Evidence can surface a real, dimension/time-window-scoped NLP enrichment aggregate from `nlp_service`.
- **Recommendation decision persistence** — `RecommendationEntity` gained nullable `decision`/`decision_note`/`decided_at` columns and a new `PATCH /recommendations/{recommendation_id}/decision` endpoint (Gateway-routed); the workspace's Decision section is now real, persisted state with loading/success/error handling, replacing the prior honest-placeholder treatment. Deliberately excludes any decision-owner/actor field — see `docs/DECISIONS.md` (REC-003).
- **Analytics honesty** — Executive Overview now computes real observations directly from already-fetched trend data instead of rendering fabricated boilerplate; Pattern Discovery, Organizational Insights, and Strategic Opportunities now render the same honest `FutureCapabilityPlaceholder` component Recommendation Effectiveness already used, replacing a fabricated recurring narrative that had been rendered with full visual parity to real data.
- **Administration integration** — Platform Overview now aggregates real, just-checked service health from all 9 backend services' `/health` endpoints (Administration's first real Gateway surface); Intelligence Configuration now displays real, read-only Business Impact engine configuration (dimension weights, impact-level point values, severity-band thresholds) sourced live from a new `business_impact_service` endpoint — no edit, save, or mutation control anywhere.

### Verified

- Full backend suite, full frontend suite, typecheck, lint, and production build all green; all 9 backend services confirmed to import and start cleanly; the recommendation-decision migration verified as a single, additive, reversible head with no branching; the full G-01 decision flow (pending/approved/rejected/deferred, optional note, server-controlled timestamp, deterministic repeated-PATCH overwrite, 404/422 handling, no actor/owner field) and the G-05 configuration read flow (real values, no secrets, no mutation route) verified end to end.
- Gateway/BFF boundary, three-model-layer separation, DATA-002 service-local read models, `incident_id` ≠ `event_id`, `recommendation_id` ≠ `incident_id`, ARB-008 stage-specific confidence, the existing error envelope/correlation-ID/timeout conventions, and the `BusinessImpactCompleted` fan-out all re-confirmed intact.
- One pre-existing, unrelated frontend test-fixture gap (from the Dashboard Supporting Evidence work) was found and corrected during closure verification.

### Explicitly Deferred

`RecommendationStatisticsService` surfacing, Root Cause confirm/reject/refresh (a write capability), Administration User & Access Management, full Dashboard dimensional filtering, editable/persisted Intelligence Configuration, Administration Audit & Change History and Data Sources & Integrations persistence, Recommendation Effectiveness/outcome tracking, and an Evaluation Service UI (explicitly decided against). Authentication/RBAC, a production message broker/Outbox/durable retry, event replay, production observability, and mTLS/service-mesh/internal authentication remain Phase 11–13 scope — see `ROADMAP.md` and `docs/DECISIONS.md` for the full list.

---

# 2026-08-09

## Phase 10 – Step 7 (Integration)

Phase 10 Step 7 has been fully implemented, hardened, and verified against real running services, completing Phase 10 (Executive Dashboard) across all seven steps. This step connects the five-workspace frontend architecture (Steps 1–6) to real backend intelligence — no workspace's real-data path renders illustrative content any longer, and the platform's first cross-service event integration is live.

### Added

- **Gateway/API integration** — a BFF-style Gateway (`gateway_service`) established as the sole public API boundary (`/api/v1/*`) for the frontend, with a centralized HTTP client, a standardized error envelope (`code`/`message`/`requestId`/`details`), correlation-ID propagation, explicit CORS origins, and bounded downstream timeouts. No workspace calls a backend service directly.
- **Dashboard integration** — `GET /api/v1/dashboard` aggregates real Operational Brief, Decision Summary, and Investigation Entry Points data; Decision Summary remains strictly descriptive, with no fabricated lifecycle or approval state.
- **Investigation vertical slice** — the canonical `/investigations/:incidentId` route now aggregates real Anomaly, Root Cause, Business Impact, and Recommendation-traceability data through the Gateway. Confidence presentation remains stage-specific (ARB-008): Business Impact never inherits Root Cause's confidence classification.
- **Recommendation read integration** — the canonical `/recommendations/:recommendationId` route surfaces only real backend fields; `recommendationId` is the resource identity, `incidentId` is preserved as traceability metadata only. Alternative Options, Expected Outcome, Risk Assessment, Decision, and Recommendation Lifecycle remain honest, unfabricated future-capability/illustrative states.
- **Analytics trend integration** — `GET /api/v1/analytics/trends` surfaces real trend data from `anomaly_service`, presented as strictly factual observations (no ranking, comparative, or causal language). Pattern Discovery, Organizational Insights, Strategic Opportunities, and Recommendation Effectiveness remain future-capability states — no backend capability exists for them yet.
- **BusinessImpactCompleted event integration** — `business_impact_service` now publishes one event per completed Business Impact assessment, delivered independently (parallel fan-out, never chained) to `recommendation_service` and `evaluation_service`. One `event_id` per occurrence is preserved end to end and kept distinct from `incident_id`; both consumers are idempotent under duplicate delivery (database-enforced event-id uniqueness). `/internal/events/*` remains internal-only — never Gateway-routed, never host-published, never frontend-facing.
- **Canonical resource routing** — Dashboard, Investigation, and Recommendation drill-down/traceability links consistently use path-based canonical routes (`/investigations/:incidentId`, `/recommendations/:recommendationId`) rather than query-string parameters.
- **Integration hardening** — a shared retry mechanism (`ErrorBoundary`'s `onRetry`/`resetKeys`) ensures a failed request can be genuinely retried, with every section sharing that fetch recovering together, not just the section whose retry control was used.

### Verified

- Real-service end-to-end verification performed against real running services (all 8 backend services, the Gateway, and PostgreSQL) and real HTTP requests: Dashboard, Investigation, Recommendation, Analytics, Administration regression (no change), and the BusinessImpactCompleted → Recommendation/Evaluation fan-out — including live duplicate-event idempotency and end-to-end identifier-integrity checks (`incident_id`, `recommendation_id`, `event_id`, `generation_id`, `evaluation_id` each confirmed to remain distinct and correctly threaded).
- Full verification suite passing: backend 837 tests (35 intentionally skipped), frontend 254 tests, typecheck, lint, and production build all green; `docker compose config` validated, with internal services confirmed to have no host-published port.
- Event delivery is explicitly single-attempt/best-effort in this prototype (no message broker, Outbox, or durable retry) — a live delivery failure was observed and confirmed not to roll back an already-persisted Business Impact assessment, consistent with the documented prototype guarantee.

### Explicitly Not Implemented (Deferred)

Recommendation Decision/Lifecycle, Recommendation Effectiveness, Analytics Pattern Discovery, Organizational Insights, Strategic Opportunities, the Administration backend, authentication/RBAC, and production event/messaging infrastructure (broker, Outbox, durable retry) — see `ROADMAP.md` and `docs/DECISIONS.md` for the full list of deferred capabilities.

---

# 2026-08-07

## Phase 10 – Step 6 (Administration Workspace Architecture)

Phase 10 Step 6 has been fully completed, reviewed, and rectified, establishing the Administration Workspace as the platform's Enterprise Control Center. No business logic, backend integration, or real administrative data was introduced — this step establishes structure and presentation model only.

### Added

- **Administration Workspace** — governs the platform itself (configuration, access management, integrations, and auditability) and has no relationship to the operational intelligence pipeline Dashboard, Investigations, Recommendations, and Analytics each participate in.
- **Six-Section Governance Architecture** — Platform Overview, User & Access Management, Data Sources & Integrations, Intelligence Configuration, Platform Governance, and Audit & Change History, each with a single, non-overlapping responsibility in a fixed reading order.
- **State / Configuration / Record Presentation Model** — a subtle, presentation-only rhythm distinguishing scanned reference sections (Platform Overview, User & Access Management, Data Sources & Integrations) from the one deliberate, consequence-aware configuration section (Intelligence Configuration) and the two historical, read-only record sections (Platform Governance, Audit & Change History) — never expressed as grouped navigation, tabs, or a wizard.
- **Explanation Before Control** — every Intelligence Configuration item presents what it is, what downstream behavior it governs, and its current value before any editing affordance is reachable; inspection is always the default state, editing is never automatic, and no configuration change is persisted anywhere in this step.
- **Calm Policy Narrative vs. Immutable Ledger** — Platform Governance presents organizational policy as calm, explanatory prose; Audit & Change History presents a permanent, read-only administrative record that deliberately excludes every activity-feed, notification, or live-updating convention.
- **Connected Services vs. Connected Systems** — platform infrastructure dependencies (Platform Overview) and external business system integrations (Data Sources & Integrations) kept visually and semantically distinct throughout, never collapsed into one undifferentiated list.
- **Administration Context** — architectural presentation state only (active section, expanded sections, and the currently-selected configuration item); no users, roles, permissions, integrations, policies, audit history, or platform status.
- **Accessibility** — correct heading hierarchy, a persistent keyboard- and screen-reader-navigable section navigator reusing the same navigator family as Investigation, Recommendation, and Analytics, and a semantic, chronologically legible audit ledger.
- **Responsiveness** — the navigator and reading column adapt from a side-by-side desktop/laptop layout to a stacked tablet/mobile layout; section order never changes, only the layout.
- **Loading** — skeleton-first loading flowing through the real section-and-card component hierarchy for every section, consistent with the discipline established in Phase 10 Steps 2–5.
- **Error Handling** — each of the six Administration sections independently error-isolated, so a failure in one section can never blank the rest of the control center.

### Verified

- Independent engineering review performed against the frozen architecture and the frozen UX specification (State/Configuration/Record rhythm, Explanation Before Control, the calm-policy-vs-ledger distinction, and the Connected Services/Connected Systems distinction).
- Full verification suite (typecheck, lint, build, automated test suite) passing with no regressions to Phase 10 Steps 1–5.

---

## Phase 10 – Step 5 (Analytics Workspace Architecture)

Phase 10 Step 5 has been fully completed and reviewed, establishing the Analytics Workspace's architecture as organizational learning drawn from operational history. No business intelligence, backend integration, or real analytics data was introduced — this step establishes structure and presentation model only.

### Added

- **Analytics Workspace** — transforms operational history into organizational learning, answering "What has the organization learned over time?" Where Dashboard owns the present at breadth and Investigation/Recommendation each own one instance in depth, Analytics owns history at breadth, the previously unclaimed quadrant.
- **Six Analytics Sections** — Executive Overview, Trend Analysis, Pattern Discovery, Recommendation Effectiveness, Organizational Insights, and Strategic Opportunities, each with a single, non-overlapping responsibility in a fixed reading order.
- **Narrative Before Charts** — Trend Analysis and Pattern Discovery each present Trend/Pattern → Narrative → Supporting Evidence; any chart remains a small, de-emphasized extension point supporting the narrative, never the section's primary content.
- **Recommendation Effectiveness** — a future-capability placeholder explaining that organizational outcome tracking does not yet exist anywhere in the platform, never a generic "No Data" or "Empty" state.
- **Shared Scope Indicator** — a single analysis-period and filter scope lives once in the persistent Analytics Navigator; no individual section restates it.
- **Strategic Opportunities** — identifies organization-level opportunities only; it never approves actions, assigns work, or manages a lifecycle, preserving Recommendation Workspace as the platform's only Decision Workspace.
- **Analytics Context** — architectural presentation state only (selected analysis period, active section, expanded sections, and selected insight); no metrics, trend data, or recommendation outcomes.
- **Accessibility** — correct heading hierarchy, a persistent keyboard- and screen-reader-navigable section navigator, and color-independent presentation throughout.
- **Responsiveness** — the navigator and reading column adapt from a side-by-side desktop/laptop layout to a stacked tablet/mobile layout; narrative order never changes, only the layout.
- **Loading** — skeleton-first loading flowing through the real section-and-card component hierarchy, driven by a real workspace-level loading transition, consistent with the discipline established in Phase 10 Steps 2–4.
- **Error Handling** — each of the six Analytics sections independently error-isolated, so a failure in one section can never blank the rest of the workspace.

### Verified

- Independent review performed against the frozen architecture and the frozen UX specification (narrative-before-charts, the future-capability placeholder, the shared Scope Indicator, and Organizational Insights' distinct-but-neutral rhythm).
- Full verification suite (typecheck, lint, build, automated test suite) passing with no regressions to Phase 10 Steps 1–4.

---

# 2026-08-05

## Phase 10 – Step 4 (Recommendation Workspace Architecture)

Phase 10 Step 4 has been fully completed, reviewed, and rectified, establishing the Recommendation Workspace's architecture as an Executive Briefing experience. No business logic, backend integration, or real recommendation data was introduced — this step establishes structure and presentation model only.

### Added

- **Recommendation Workspace** — transforms operational understanding into an explainable, governed operational decision while preserving human oversight. The platform recommends; humans decide. Represents recommendation review → human decision → recommendation lifecycle, and is explicitly not workflow, approval, or task-management software.
- **Executive Briefing Workspace UX** — a single-column, memo-style reading flow: typography before decoration, narrative-first exploration, progressive disclosure, and Decision Before Lifecycle as the guiding sequence.
- **Recommendation Overview** — the canonical statement of what is being recommended.
- **Recommendation Rationale** — explains why the recommendation exists by referencing the Investigation's own findings, without duplicating them, and traces back to the originating Incident.
- **Alternative Options** — a future-capability placeholder explaining why comparison against other considered options isn't available yet, never a generic "No Data" or "Empty" state.
- **Expected Outcome** — the operational, customer, financial, and risk-reduction improvement the recommendation expects to achieve.
- **Risk Assessment** — trade-offs, uncertainty, implementation risk, and business risk, given a visually distinct grouping while remaining calm — never warning styling, alarm colors, or alarm visuals.
- **Decision** — represents the human decision (Pending Review, Approved, Rejected, or Deferred) as data only; no approval, rejection, or workflow controls exist anywhere in the workspace.
- **Recommendation Lifecycle** — represents the recommendation after a decision has been made, with Decision Before Lifecycle enforced structurally: no stage progression is shown until a decision exists, and Rejected/Deferred are each represented on their own terms rather than as an incomplete Approved path.
- **Recommendation Context** — architectural presentation state only (active section, expanded sections, and recommendation/incident references); no business state, no backend state.
- **Accessibility** — correct heading hierarchy, a persistent keyboard- and screen-reader-navigable section navigator, and color-independent decision/status presentation throughout.
- **Responsiveness** — the navigator and reading column adapt from a side-by-side desktop/laptop layout to a stacked tablet/mobile layout; narrative order never changes, only the layout.
- **Loading** — skeleton-first loading flowing through the real section-and-card component hierarchy for every section, consistent with the discipline established in Phase 10 Steps 2–3.
- **Error Handling** — each of the seven Recommendation sections independently error-isolated, so a failure in one section can never blank the rest of the briefing.

### Verified

- Independent engineering review performed against the frozen architecture and the frozen UX specification (persistent calm Decision reference, Risk Assessment's distinct-but-calm treatment, the future-capability placeholder, and reuse of Investigation's navigation model).
- Full verification suite (typecheck, lint, build, automated test suite) passing with no regressions to Phase 10 Steps 1–3.

---

## Phase 10 – Step 3 (Investigation Workspace Architecture)

Phase 10 Step 3 has been fully completed and reviewed, establishing the Investigation Workspace's architecture. No business logic, backend integration, or real Incident data was introduced — this step establishes structure and presentation model only.

### Added

- **Investigation Mission** — the Investigation Workspace exists to transform operational signals into explainable operational understanding through evidence-driven analysis, enabling confident human decisions. Investigation is explicitly not a new domain entity: it is the structured presentation of a single Incident, the platform's existing central lifecycle object.
- **Evidence Before Conclusions** — the workspace's guiding principle, enforced structurally: Evidence is always presented before Root Cause Analysis, and no section states a conclusion without supporting evidence already on the page above it.
- **Narrative-First Navigation** — a persistent `InvestigationNavigator` keeps every section directly and independently reachable at all times; the workspace behaves as a structured investigation document, never a wizard.
- **Five Investigation Sections** — Observation ("what happened?"), Evidence ("why should I believe this?"), Root Cause Analysis ("why did this happen?"), Business Impact ("why should the organization care?"), and Recommended Next Step ("what should happen next?"), each with a single, non-overlapping responsibility.
- **Investigation Context** — architectural presentation state only: an Incident reference, active section, expanded sections, and selected evidence. No backend state, no business state.
- **Business Impact Taxonomy** — Business Impact consistently presents the platform's approved five dimensions (Financial, Customer, Operational, SLA, Reputation), matching the Business Impact Engine's own frozen model exactly.
- **Stage-Specific Confidence Presentation** — Root Cause Analysis and Business Impact each present confidence through one shared visual language that always states what it measures, keeping the two values legible as distinct, non-comparable measurements rather than one unified score.
- **Context-Preserving Recommendation Handoff** — the Recommended Next Step's transition into Recommendations already carries the originating recommendation's identity, so a future step can open Recommendations pre-scoped to it rather than a generic queue.
- **Accessibility** — correct heading hierarchy, a real keyboard- and screen-reader-navigable section navigator, and color-independent confidence and status presentation throughout.
- **Responsiveness** — the navigator and reading column adapt from a side-by-side desktop/laptop layout to a stacked tablet/mobile layout; narrative order never changes, only the layout.
- **Loading Architecture** — skeleton-first loading flowing through the real section-and-card component hierarchy, consistent with the discipline established in Phase 10 Step 2.
- **Error Isolation** — each of the five Investigation sections independently error-isolated, so a failure in one section can never blank the rest of the investigation.

### Verified

- Independent Product Architecture Review performed before implementation began, evaluating the proposed Investigation architecture against the Product Experience Guide and the platform's existing ADRs (ARB-006 Evidence Chain, ARB-007 Incident as the central lifecycle object, ARB-008 stage-specific confidence, BI-002 the five-dimension taxonomy).
- All four clarifications the review required before implementation are directly encoded in the implementation, not left as documentation-only intent.
- Full verification suite (typecheck, lint, build, automated test suite) passing with no regressions to Phase 10 Steps 1–2.

---

## Phase 10 – Product Architecture Refinement (Workspace Consolidation)

Following a Product Architecture Review conducted before Phase 10 Step 3 scoping began, the frozen six-workspace architecture was refined to five workspaces. This is a navigation and ownership refinement, not a redesign: Dashboard, Investigations, Recommendations, Analytics, and Administration were not altered beyond updated ownership language, and no business functionality was added.

### Changed

- **Action Center retired as a standalone workspace.** Its route, navigation entry, workspace component, and dedicated icon were removed.
- **Recommendations now owns the complete operational decision and action lifecycle** — recommendation review, approval, rejection, implementation status, monitoring, and completed actions — absorbing Action Center's decision-and-action responsibility. Structure only; no approval/rejection workflow was implemented.
- **Navigation** updated so Dashboard flows directly into Investigations; the sidebar, breadcrumbs, and router all derive from the same single navigation configuration, so no other component required a corresponding change.
- **Architecture Decision Record FE-001** added to `docs/DECISIONS.md`, recording the rationale, migration impact, and long-term benefit of the consolidation.

### Verified

- Every reference to Action Center (route, navigation entry, workspace registration, exports, icon, and documentation cross-references) was located and removed or updated; none remain.
- Full verification suite passing (typecheck, lint, build, automated test suite) with no regressions.
- No architectural drift: Dashboard, Investigations, Analytics, and Administration are unchanged; Recommendations' existing implementation was extended, not rebuilt.

---

## Phase 10 – Step 2 (Dashboard Information Architecture)

Phase 10 Step 2 has been fully completed, reviewed, and rectified, establishing the Dashboard's complete information architecture within the Step 1 application shell. No business intelligence, backend integration, or real analytics were introduced — this step establishes structure and presentation model only.

### Added

- **Dashboard Information Architecture** — The Dashboard implemented as one cohesive operational workspace across four architectural sections in a fixed order, each with an exclusive, non-overlapping responsibility.
- **Operational Brief** — Situational-awareness architecture: Overall Operational Status, Critical Situations, Key Changes, Recommended Focus, and Operational Health Snapshot, following the Hybrid Time Model and a Stability Philosophy that confidently communicates a healthy state rather than manufacturing urgency.
- **Decision Summary** — Decision Opportunity architecture supporting human judgment, deliberately distinct from a work queue, alert list, or recommendation table.
- **Investigation Entry Points** — The Operational Story presentation model: the Dashboard's narrative view of the Incident lifecycle (Complaint → Incident → Root Cause → Business Impact → Recommendation), never exposing backend entities directly.
- **Supporting Evidence** — Analytics-placeholder architecture that supports the conclusions already presented above it, never competing with them for primary understanding.
- **Global Dashboard Context** — A single shared scope (time range, region, business unit, product/user scope) owned by the Dashboard and consumed consistently by every section, so sections can never disagree about what they're showing.
- **Universal Information Hierarchy** — Headline → Primary Insight → Why It Matters → Supporting Context → Suggested Next Step → Drill-down, encoded structurally and reused by every section rather than reinvented per section.
- **Dashboard Component Architecture** — Composable, single-responsibility components organized by section, extending rather than duplicating the Step 1 shared foundation (layout, feedback, navigation, and page components).
- **Loading Architecture** — Skeleton-first loading states flowing through the real section-and-card component hierarchy, preserving layout stability.
- **Error Isolation** — Each of the four Dashboard sections independently error-isolated, so a failure in one section can never blank the sections around it.
- **Empty-State Philosophy** — Confident, honest empty states ("no critical situations," "no decisions require attention") in place of fabricated data or generic "No Data" messaging.
- **Accessibility Improvements** — Correct, non-fragmented heading and landmark structure, keyboard and screen-reader support, and color-independent status communication throughout.
- **Responsiveness** — Consistent information hierarchy across desktop, laptop, tablet, and mobile via the existing responsive layout foundation.

### Verified

- Independent Engineering Review Board review performed against the frozen Dashboard architecture, Product Experience Guide, and Universal Information Hierarchy.
- Two required implementation rectifications completed (loading-state wiring through the real component hierarchy; reduced landmark fragmentation in Operational Brief) and three optional improvements completed (shared drill-down affordance, data-injectable section content, data-derived loading state).
- No architectural drift identified at any point in implementation, review, or rectification.
- Full verification suite (typecheck, lint, build, automated tests) passing with no regressions to Phase 10 Step 1.

---

# 2026-08-04

## Phase 10 – Step 1 (Product Workspace Architecture)

Phase 10 Step 1 has been fully completed, establishing the foundational frontend product workspace architecture.

### Added

- **Product Workspace Architecture** — Established the core structural boundaries for the frontend application.
- **Application Shell & Navigation** — Implemented the persistent Application Shell, Sidebar, Top Navigation, and Workspace Routing.
- **Shared Component Foundation** — Created the shared structural components and Workspace Component Architecture.
- **Design System Foundation** — Built the comprehensive design system, including Theme Foundation, Responsive Foundation, and Accessibility Foundation.
- **UX & Interaction Foundations** — Implemented Motion Foundation, Loading Foundation, Error Boundary Architecture, and Placeholder Architecture.
- **Testing & Performance** — Introduced Lazy Loaded Workspaces and Frontend Testing Foundation.

### Verified

- Implementation Verification confirmed no architectural drift.
- All architectural requirements satisfied and architecture is fully compliant.

---

# 2026-08-01

## Phase 9 – Step 3 (Execution Lifecycle)

Phase 9 Step 3 has been fully completed, successfully introducing the event-driven execution lifecycle around the frozen Recommendation Domain Engine and persistence layer. The Recommendation Engine itself remains pure and unchanged.

### Added

- **`RecommendationLifecycleService`** — Application service that coordinates the complete execution lifecycle. It validates eligibility, performs the fast application-level idempotency check, creates the `generation_id`, owns the transaction boundary (commit/rollback), invokes the orchestrator, and publishes the `RecommendationsGenerated` event.
- **`RecommendationOrchestrator`** — Application service that invokes the Domain Engine and coordinates persistence via the Repository. It does not handle lifecycle validation or events.
- **Database-Backed Idempotency** — Relies on a `UNIQUE(event_id)` database constraint and catching `DuplicateGenerationEventError` to guarantee safety against concurrent duplicate events.
- **`BusinessImpactCompleted` Consumer** — Infrastructure event consumer that deserializes the inbound event and translates it into an Application request.
- **`RecommendationsGenerated` Publisher** — Infrastructure event publisher. Emits a lightweight event containing generation metadata and recommendation summaries (category, priority, action, short rationale) but excludes heavy JSONB evidence payloads to avoid bloat.
- **Zero Recommendation Execution** — Properly modeled: if the engine returns zero recommendations, a generation is still persisted and published as a meaningful audit event.

### Verified

- Clean Architecture: Layers and boundaries are strictly preserved.
- DDD: The Domain Engine remained untouched and pure.
- Transaction Design: Commit only happens on success, and events are only published after a successful commit.
- Concurrency: Database-backed uniqueness guarantees idempotency.

---

## Phase 9 – Step 2 (Persistence & APIs)

Phase 9 Step 2 has been fully completed, successfully introducing PostgreSQL persistence, read-only REST APIs, and application-level statistics around the frozen Recommendation Domain Engine. The concept of `RecommendationGeneration` was introduced strictly as an execution-grouping and historical auditing persistence mechanism, preventing persistence concerns from polluting the domain.

### Added

- **`RecommendationEntity` & `RecommendationGenerationEntity`** — SQLAlchemy models providing a hybrid relational/JSONB persistence model. Relational columns support rapid filtering/sorting, while JSONB holds unstructured explainability data. Added `action` as a relational column to correct an omission in the frozen architecture and preserve aggregate integrity.
- **`RecommendationRepository`** — cleanly separated repository implementation including atomic `save_many()` operations that commit a full Generation alongside its Recommendations.
- **REST APIs** — strictly read-only endpoints covering `/recommendations`, `/recommendations/latest`, and generation-level lookups. Creation remains explicitly deferred to Step 3.
- **Lightweight DTOs (Summary vs. Full)** — addressed payload bloat by projecting a `RecommendationSummaryResponse` (omitting heavy JSONB) for list views, and a `RecommendationFullResponse` for singular item lookups.
- **`RecommendationStatisticsService`** — application-layer service dynamically aggregating generation-level statistics.
- **Alembic Migration** — automatically tracked database migration for the new tables.

### Verified

- Comprehensive unit, repository, API, and integration testing for all read flows and atomic persistence.
- Verified Full DTO vs. Summary DTO projections correctly strip heavy payloads.
- Verified composite database indexing properly supports the "latest" generation queries.
- Independent principal-engineer-level engineering review performed: the implementation cleanly separates domain logic from infrastructure, handles idempotency modeling well, and strictly follows the frozen architecture (with the documented exception of the `action` column).

---

## Phase 9 – Step 1 (Recommendation Decision Engine)

Phase 9 Step 1 has been fully completed: a pure, deterministic, in-memory domain engine converting completed operational intelligence into explainable Recommendations. No database, repository, REST API, messaging, lifecycle, transaction, or dependency-injection code was introduced -- those are explicitly scoped to Step 2 and Step 3. No existing service was modified.

### Added

- **`IntelligenceContext`** — the engine's single immutable input Domain Value Object, aggregating local, persistence-independent views of Incident, BusinessImpactSummary, RootCauseSummary (optional), NLPIntelligence (optional), and AnomalyIntelligence (optional). `incident`/`business_impact` are required, per the frozen invariant that a Recommendation cannot exist without them.
- **`Recommendation`** — the immutable aggregate (category, action, priority, score, rationale, priority rationale, supporting evidence), with every domain invariant enforced in `__post_init__`.
- **`RecommendationCategory`** (8 values) and **`RecommendationPriority`** (4 tiers) — Domain Enums, preventing free-text classification.
- **`SupportingEvidence`** / **`EvidenceSource`** — structured, weighted, explainable evidence, mirroring Root Cause Service's own `Evidence` pattern.
- **`scoring.py`** — the single, shared Recommendation Scoring Policy every rule and the Consolidator's merge path call into; deliberately no post-processing normalizer, per the ARB's mitigation for cross-rule score inconsistency.
- **`precedence.py`** — the shared Category/Priority precedence policy backing the Consolidator's deterministic ordering (Priority → Category Precedence → Score → Rule Evaluation Order).
- **Eight `RecommendationRule` implementations**, one per category (`EscalationRule`, `MitigationRule`, `SLAProtectionRule`, `InfrastructureActionRule`, `OperationalActionRule`, `CustomerCommunicationRule`, `InvestigateRule`, `MonitorRule`) — independent, deterministic, never calling each other.
- **`RecommendationConsolidator`** — the dedicated Domain Service that deduplicates, merges equivalent recommendations, resolves the one defined conflict (MONITOR vs. a genuinely more urgent category), and applies deterministic ordering. Never fabricates a Recommendation of its own.
- **`RecommendationEngine`** — orchestrates `IntelligenceContext → rules → raw Recommendations → Consolidator → final collection`, entirely in-memory.

### Verified

- 126 new tests added; full `backend` suite (660 tests) passing, no regressions.
- Determinism and immutability verified directly, per component, not just at the engine level.
- Final engineering review performed: no architectural drift, no implementation changes required. One architectural question -- Rules organized by Category vs. by Business Policy -- was raised and resolved in favor of the current design; see `docs/DECISIONS.md` (REC-001).

### Architectural note (reported, not silently resolved)

`root_cause_service` and `business_impact_service` place their rule engines under `app/services/`; `evaluation_service` (and now `recommendation_service`) place theirs under `app/domain/`, per the frozen architecture's explicit Domain-layer vocabulary for every in-scope component. No existing service was modified to reconcile this; the inconsistency between the two older services and the two newer ones is documented here rather than silently copied forward.

---

# 2026-07-28

## Phase 8 – Step 3 (Execution Lifecycle)

Phase 8 Step 3 has been fully completed, introducing the event-driven execution lifecycle around the frozen Step 1/Step 2 engine and persistence layer. No changes were made to the Evaluation engines, `Evaluation` aggregate, or the existing read-only REST API contract.

### Added

- **`EvaluationLifecycleService`** (`application/lifecycle/`) — coordinates the complete execution lifecycle for one inbound `BusinessImpactCompleted` event: execution eligibility, the fast application-level idempotency check, transaction ownership (commit only after successful persistence, rollback on every failure path), invoking `EvaluationOrchestrator`, and publishing `EvaluationCompleted` only after a successful commit.
- **`BusinessImpactCompletedConsumer`** (`infrastructure/messaging/consumers/`) — deserializes the inbound event payload and translates it into the Application-owned `EvaluationExecutionRequest`; performs no validation, repository access, or computation of its own.
- **`InProcessEventPublisher`** (`infrastructure/messaging/publishers/`) — the current, broker-less implementation of the `EventPublisher` port. No message broker (RabbitMQ/Kafka/Redis) exists anywhere in this repository yet; publishing is implemented as a logged, in-process operation behind the same port a real broker adapter would implement later, with zero impact on `EvaluationLifecycleService` or anything above it.
- **`event_id` column on `evaluations`** (new Alembic migration, `a2f5c8e1d3b7`) — nullable, UNIQUE. This is the database-backed correctness guarantee behind the idempotency check: verified under a genuine two-connection concurrent-write test against real PostgreSQL, not just asserted.
- **`EvaluationRepository.save()`** extended (backward-compatible, additive) to accept optional `event_id`/`root_cause_id`/`business_impact_id`, and a new `get_by_event_id()` read operation — closing the lineage gap Step 2 documented as deliberately deferred (`root_cause_id`/`business_impact_id` were always `None` until a future step's event consumer supplied them).
- **`POST /internal/events/business-impact-completed`** — a thin, unversioned internal route standing in for a real broker subscription, exposing the Consumer over HTTP so it is genuinely invocable today.

### Verified

- 123 tests in `evaluation_service` (up from 87), all passing against real PostgreSQL: consumer (success/malformed payload/retryable infrastructure exception/deterministic rejection), lifecycle service (success/duplicate event/validation rejection/orchestrator failure/publisher failure/rollback/unreachable database), orchestrator lineage passthrough, repository UNIQUE-constraint and real concurrent-duplicate protection, and HTTP integration tests for the happy path and every failure scenario.
- Full `backend` test suite: 550 passed, no regressions in any other service.
- Independent architecture-compliance review performed: every layer's Must/Must-Not responsibilities verified by direct code inspection against the frozen Step 3 architecture, with one Clean Architecture finding (Application-layer code referencing a concrete SQLAlchemy type) identified for follow-up.

### Deviations (explicitly reviewed, not silent)

- No message broker exists anywhere in this repository (confirmed by inspection before implementation began: no broker in `docker-compose.yml`, no client library in any service's `requirements.txt`, no shared event-schema module). The Consumer/Publisher are therefore in-process Infrastructure adapters behind Application-owned ports rather than real broker clients — see `docs/DECISIONS.md` (EVAL-001).
- `EvaluationOrchestrator` was extended in place rather than relocated to a new `application/orchestration/` package: it already existed, was already correctly scoped to the frozen Step 3 responsibilities, and relocating it would only churn imports across the existing test suite with no behavioral benefit.

---

# 2026-07-26 / 2026-07-27

## Phase 8 – Step 2 (Persistence & APIs)

Phase 8 Step 2 introduced persistence and read-only REST APIs around the frozen Step 1 Evaluation Engine.

### Added

- `EvaluationRecord` (Domain envelope giving the identity-less Step 1 `Evaluation` aggregate a persisted identity), `EvaluationRepository` port, `PostgreSQLEvaluationRepository`, `EvaluationModel` (JSONB-backed ORM model, `clock_timestamp()`-based ordering, composite index on `incident_id`/`evaluation_version`), and `EvaluationModelMapper`.
- Read-only REST API: `GET /evaluations`, `/evaluations/statistics`, `/evaluations/latest/{incident_id}`, `/evaluations/history/{incident_id}`, `/evaluations/{evaluation_id}` — no write endpoints exist (verified: POST/PUT/PATCH/DELETE all return 405).
- `EvaluationStatisticsService` (Application-layer aggregation, per the frozen decision not to add a repository-level `list_statistics()` method).
- Alembic migration `1185033beadf` (`evaluations` table).

### Verified

- 87 tests passing (added a dedicated multi-page pagination test for `EvaluationStatisticsService.compute()`'s internal scan loop on 2026-07-27, closing the one test-coverage gap identified during engineering review).
- Independent principal-engineer-level implementation review performed: no blocking issues found; DDD/Clean Architecture/Repository Pattern boundaries confirmed correctly held.

---

## Phase 8 – Step 1 (Evaluation Engine)

Phase 8 Step 1 introduced the deterministic Evaluation Engine as a pure, persistence-independent Domain component.

### Added

- `ValidationEngine`, `QualityEngine`, `ExplainabilityEngine`, `ConfidenceAnalyzer`, `EvaluationBuilder`, and the immutable `Evaluation` aggregate (identity-less by design — identity assignment is deliberately a Step 2 persistence-layer concern).
- `EvaluationOrchestrator` (Application layer) coordinating Validation → [Quality Engine ‖ Explainability Engine] → Confidence Analyzer → Evaluation Builder, running the two independent engines concurrently via `asyncio.gather`.
- `CompletedIntelligence` / `DomainEvaluationContext` — plain, persistence-independent input DTOs, deliberately not importing the Root Cause or Business Impact services' own domain/ORM types (DATA-002).

### Verified

- New unit test suite covering every engine and the orchestrator, all passing. Pure in-memory domain logic — no SQLAlchemy, ORM, or persistence involved at this step.

---

# 2026-07-24

## Phase 7 – Step 3 (Business Impact Lifecycle & Validation)

Phase 7 Step 3 has been fully completed. This was a validation-only phase: no changes were made to the Business Impact Engine, its rules, the persistence model, or the REST API contract.

### Added

- **`fakes.py`** — shared, in-memory test-support module (Fake repositories + a realistic, hand-computable synthetic Incident/RootCause scenario builder), used across the new lifecycle test suite.
- **`test_business_impact_lifecycle_e2e.py`** — full lifecycle validation (Incident → Root Cause Summary → Engine → Assessment → Persistence → Repository → DTO), verifying every field against independently hand-computed expectations.
- **`test_api_business_impact_lifecycle.py`** — deeper API integration tests wiring the real Application Service and real Engine through the real FastAPI routes (only the repository layer is Faked), covering creation, retrieval by assessment id, retrieval by incident id (via the existing list filter), list filtering, enum/timestamp serialization, and every documented error path.
- **`test_determinism.py`** — proves identical inputs produce an identical `BusinessImpactAssessment` (scores, severity, priority, explanation) across repeated runs at the engine, application-service, and REST API levels.
- **`test_explainability_contract.py`** — proves the Engine's explanation string is preserved character-for-character through the ORM entity, the response DTO, and full JSON encode/decode, across a quiet, a critical, and a mixed scenario.
- **`backend/services/business_impact_service/README.md`** rewritten to document the verified lifecycle, the actual REST endpoints, what Step 3 verified, and how downstream services should consume this service's data (via a DATA-002 read model, anchored on Incident per ADR-007).

### Verified

- 42 new tests added; 427 / 427 total repository tests passing (385 pre-existing + 42 new).
- mypy clean across all new production and test code.
- Live verification performed against a running PostgreSQL instance (`docker compose up postgres business_impact_service`), using real, already-persisted Incident and Root Cause records from prior pipeline phases: creation, retrieval, list filtering, every documented error path, and determinism across three repeated real requests all confirmed correct. Verification-only rows were removed and containers stopped afterward, leaving the environment as found.
- Zero architectural drift: the Business Impact Engine, Root Cause logic, persistence model, and API/DTO contracts are byte-for-byte unchanged from Phase 7 Step 2.

---

## Architecture Review Board — Documentation Alignment

The Architecture Review Board (ARB) reviewed the platform's complete product vision and long-term architecture, independent of current implementation. Eight architectural decisions were approved and the documentation set was aligned to reflect them.

### Added

- **`docs/ADR_ARCHITECTURE_REVIEW_BOARD.md`** — full ARB session record: purpose, context, review summary, all eight approved decisions, architectural rationale, and long-term vision.
- **`docs/DECISIONS.md`** — eight new ADR entries (ARB-001 through ARB-008) recorded in the permanent decision ledger.

### Changed

- **Terminology aligned:** "Business Risk" → "Business Impact" across `PROJECT_BRAIN.md` and `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md`.
- **Platform identity clarified** (ADR-001) in `PROJECT_BRAIN.md`, `PRD.md`, `ARCHITECTURE.md`, and `README.md`.
- **Long-term intelligence lifecycle vision** (ADR-002, ADR-005) added to `PROJECT_BRAIN.md`, `ARCHITECTURE.md`, `ROADMAP.md`, and `README.md`, explicitly marked as post-MVP and non-binding on the current roadmap.
- **Business Impact Engine framing corrected** (ADR-003) in `PRD.md` and `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md` to reflect the actual five-dimension, generic, deterministic engine rather than legacy scalar risk-score language.
- **Presentation Layer clarified** (ADR-004) in `ARCHITECTURE.md`, `PRD.md`, and `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md`: dashboard/copilot adapt explanation, never the engine.
- **Evidence chain** named conceptually (ADR-006) in `PROJECT_BRAIN.md` and `ARCHITECTURE.md`.
- **Incident's role as the central lifecycle object clarified** (ADR-007): `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md`'s Root Cause Service section was corrected — it previously described a generic `complaint_event_links` ownership that contradicted Root Cause Service's actual, already-implemented consumption of correlated Incidents. `PROJECT_BRAIN.md` and `ARCHITECTURE.md` now name Incident explicitly as this central object.
- **Confidence clarified as stage-specific** (ADR-008) in `ARCHITECTURE.md`, `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md`, and `DOMAIN_ENUMS_AND_OPERATIONAL_CONSTANTS.md` (new "Confidence Philosophy" section).
- **`docs/PROJECT_STATUS.md`**: added an Architecture Governance section referencing the ARB; corrected a pre-existing internal inconsistency (top status block still read "Step 2 – Ready to Begin" while the rest of the same document already showed Step 2 complete and Step 3 as current focus).

### Verified

- No MVP scope change.
- No completed phase changed.
- No frozen engine (Root Cause Rule Engine, Business Impact Analysis Engine) modified.
- No new service introduced.
- Documents outside the eight ADRs' subject matter (`DATA_MODEL.md`, `DATABASE_SCHEMA_ARCHITECTURE.md`, `ENTITY_MODELING_AND_OWNERSHIP.md`, `CORE_ENTITY_SPECIFICATIONS.md`, `MVP_DATASET_SCOPE.md`, `DATASET_AND_INGESTION_STRATEGY.md`, `REPOSITORY_STRUCTURE.md`) were reviewed and intentionally left unchanged — their content is schema/tooling-level and not addressed by this ARB session.

---

## Phase 7 – Step 2 (Business Impact Persistence & APIs)

Phase 7 Step 2 has been fully completed, introducing the persistence layer and REST APIs for the Business Impact Engine, while strictly maintaining the purity of the deterministic domain engine.

### Added

- **BusinessImpactAssessmentEntity** — SQLAlchemy ORM model representing a persisted impact assessment.
- **Alembic Migration** — database schema changes for `business_impact_assessments`.
- **Repository Layer** — `BusinessImpactRepository` for CRUD operations, plus `IncidentReadRepository` and `RootCauseReadRepository` utilizing service-local read models (`read_models.py`) to respect DATA-002 constraints.
- **Mapper Layer** — `BusinessImpactInputMapper` and `BusinessImpactOutputMapper` that enforce the boundary between persisted ORM entities and the pure domain value objects.
- **Application Service** — `BusinessImpactApplicationService` orchestrating the load -> map -> analyze -> persist -> return workflow without duplicating logic.
- **REST APIs** — Endpoints in `business_impact.py` for creating assessments from an incident ID (`POST /business-impact`) and retrieving them (`GET /business-impact`, `GET /business-impact/{id}`).

### Verified

- API Contract (`POST /business-impact` accepts ONLY `incident_id`).
- Mapper layer strictly performs translation with documented deterministic defaults (`sla_breach_count=0`, `negative_sentiment_ratio=0.0`).
- Repository layer strictly returns persistence/read models.
- Application Service strictly manages orchestration.
- Zero architectural drift detected from the approved Phase 7 Step 2 design.

---

# 2026-07-22

## Phase 7 – Step 1 (Business Impact Analysis Engine)

Phase 7 Step 1 has been fully completed, delivering a pure, deterministic Business Impact Analysis Engine. The engine evaluates an Incident and its identified Root Cause across five business dimensions to produce an immutable, fully explainable `BusinessImpactAssessment`.

### Added

- **Business Impact Analysis Engine** — deterministic orchestration engine accepting an injected sequence of `ImpactRule` instances.
- **`ImpactRule` abstraction** — abstract base class placed in the domain layer enforcing a single evaluation contract per rule.
- **`FinancialRule`** — evaluates financial impact based on root cause type and complaint volume growth.
- **`CustomerRule`** — evaluates customer impact based on estimated affected customer count and urgency.
- **`OperationalRule`** — evaluates operational impact based on root cause type and anomaly severity.
- **`SLARule`** — evaluates SLA impact based on SLA breach count and urgency annotations.
- **`ReputationRule`** — evaluates reputational impact based on sentiment ratio, confirmed sentiment shifts, and multi-region spread.
- **`ImpactEvaluation`** — immutable value object carrying dimension, level, and deterministic reason string.
- **`BusinessImpactProfile`** — structured container for all five named `ImpactEvaluation` fields with an `all_evaluations()` helper.
- **`BusinessImpactAssessment`** — immutable final domain output with the exact 13 specified fields. No ORM metadata. No timestamps.
- **Centralized weighting** — `weighting.py` centralizes dimension weights (Financial 35%, Customer 25%, Operational 15%, SLA 15%, Reputation 10%).
- **Deterministic explanation generation** — `explanation.py` aggregates `ImpactEvaluation` reason strings without duplicating business logic.
- **`scoring.py`** — centralizes level-to-points conversion, weighted aggregation, severity band mapping, priority assignment, and the completeness-based confidence heuristic.
- **Local input value objects** — `Incident`, `RootCauseSummary`, `TrendMetrics`, `AnomalyMetrics` as persistence-independent domain inputs, consistent with the service-isolation convention established in Phase 6 (RCA-001).

### Testing

- 85 new unit tests added covering all domain models, rules, engine orchestration, scoring, weighting, and explanation.
- **356 / 356** total repository tests passing (271 pre-existing + 85 new).
- mypy clean across 31 files in the new module.

### Verification

- Architecture reviewed by Principal Software Architect prior to implementation.
- Architecture reviewed post-implementation. No architectural drift identified.
- Zero modified files — all prior-phase code, tests, and APIs remain completely untouched.
- Phase officially frozen.

---

# 2026-07-21

## Phase 6 Complete (Root Cause Analysis)

Phase 6 has been fully completed, delivering a deterministic, explainable Root Cause Analysis engine that is now fully integrated into the platform with persistence, REST APIs, and operational lifecycle management.

### Major Capabilities Introduced:
- **Deterministic Rule Engine:** Specification-pattern rules evaluate Incidents and produce fully explainable RootCauseCandidates.
- **Persistence & APIs:** Root Cause records are persisted in PostgreSQL with a complete REST API surface.
- **Lifecycle Management:** Root Causes can be confirmed, rejected, or recalculated via explicit lifecycle transitions enforced by the LifecycleValidator.

---

## Phase 6 – Step 3

### Added

- Lifecycle Validator with deterministic state machine enforcement.
- Confirm operation (`PATCH /api/v1/root-causes/{id}/confirm`).
- Reject operation (`PATCH /api/v1/root-causes/{id}/reject`).
- Refresh/Recalculation operation (`POST /api/v1/root-causes/{id}/refresh`).
- Terminal state protection (CONFIRMED and REJECTED states are protected from invalid transitions).
- UNKNOWN result handling on refresh (explicit handling when Rule Engine returns no matching candidate).

### Verified

- Lifecycle transition unit tests passing.
- Invalid transition rejection tests passing.
- Integration tests for all three new endpoints.
- Full repository regression suite passing.
- End-to-end pipeline validated via Docker and PostgreSQL.
- Rule Engine confirmed completely unchanged.

---

## Phase 6 – Step 2

### Added

- RootCause persistence layer (SQLAlchemy model, JSON evidence, Alembic migration).
- RootCause and Incident Read Repositories maintaining CRUD boundaries.
- Mapper layer (`RootCauseMapper`, `IncidentMapper`) to strictly isolate Domain logic from ORM objects.
- `RootCauseApplicationService` to orchestrate mapping, inference, and persistence.
- REST APIs (`POST /api/v1/root-causes`, `GET /api/v1/root-causes/{id}`, etc.).

### Verified

- 26 integration tests and 232 repository tests passing.
- Complete end-to-end Root Cause pipeline validated via Docker and PostgreSQL.
- Strict adherence to Clean Architecture and DATA-002 (no ORM leakage into the Domain Engine).

---

## Phase 6 – Step 1

### Added

- Deterministic Root Cause Rule Engine.
- Specification Pattern for rule evaluation.
- `RuleRegistry` and Rule Versioning.
- `RootCauseCandidate` domain object.
- Structured Evidence and Confidence scoring models.
- Five independent deterministic rules (Payment, Logistics, Service Outage, Inventory, Customer Support).
- Persistence-independent `Incident` domain input model.

### Verified

- 56/56 new unit tests passed.
- 210/210 full repository tests passed.
- Smoke tests and Pyflakes checks passed.
- Pure in-memory domain logic (no SQLAlchemy, ORM, APIs, or dependency injection).

---

# 2026-07-20

## Phase 5 Complete (Trend, Anomaly & Incident Correlation)

Phase 5 has been fully completed, successfully introducing the platform's core operational intelligence engine. The Anomaly Service is now stable and capable of detecting emerging risks before escalating them to the future Root Cause Engine.

### Major Capabilities Introduced:
- **Trend Analysis:** Real-time metrics aggregation across volumes, sentiments, and urgencies.
- **Anomaly Detection:** Deterministic spike detection with lifecycle tracking and stable fingerprinting.
- **Incident Correlation:** Grouping related anomalies into higher-level incidents, reducing noise and focusing investigations.

---

## Phase 5 – Step 3

### Added
- Incident Correlation Engine
- Incident grouping logic for related anomalies
- Transition structures preparing for Phase 6 Root Cause Analysis

---

## Phase 5 – Step 2

### Added

- Active anomaly lifecycle management
- Historical anomaly tracking
- Fingerprint-based identity
- Explainability layer
- Five deterministic detectors
- REST API endpoints
- Alembic migration

### Changed

- Centralized severity model
- New anomaly enums

### Validation

- Live Docker verification
- PostgreSQL migration verification
- OpenAPI verification
- Full test suite passing

---

# 2026-07-19

## Phase 5 – Step 1

### Added

- Trend Analysis Engine (`TrendEngine`) for the Anomaly Service, orchestrating five modular aggregators.
- Modular aggregators: `VolumeAggregator`, `CategoryAggregator`, `RegionAggregator`, `SentimentAggregator`, `UrgencyAggregator` — each with a single responsibility.
- `TrendRepository` for read-only, SQL-side aggregation queries against `complaints` and `complaint_enrichments`.
- Six read-only trend endpoints: `/trends`, `/trends/daily`, `/trends/categories`, `/trends/regions`, `/trends/sentiment`, `/trends/urgency`.
- Architectural decision DATA-002 for service-local read models.

### Changed

- Registered the trends router in the Anomaly Service's application entrypoint.

### Verified

- Full Anomaly Service test suite and full-repository test suite passing.
- Docker Compose build and startup for the Anomaly Service alongside Postgres, the Ingestion Service, and the NLP Service.
- OpenAPI schema generation.
- All six trend endpoints against real seeded and NLP-enriched data.
- No database changes: metrics are computed dynamically from existing tables, with no new migrations.

### Notes

- Purely descriptive, explainable analytics — no anomaly detection, severity scoring, or persistence introduced in this step; reserved for Phase 5 Step 2.

---

## Phase 4 – Step 4

### Added

- Architectural decision DATA-001 for database-level referential integrity across boundaries.

### Changed

- Replaced monolithic `classifiers.py` and `text_processing.py` utilities with decoupled modular services (`SentimentAnalyzer`, `UrgencyAnalyzer`, `CategoryClassifier`, `KeywordExtractor`, `Summarizer`).
- Ensured deterministic orchestration service captures explainability metadata effectively.

### Fixed

- Removed all dead code and imports related to deprecated NLP utility modules.

### Verified

- Full test suite execution.
- Docker builds and API schema loading.
- Explainability metadata persistence.
- Project documentation updates.

---

## Phase 4 – Step 3

### Added

- Complaint enrichment REST API.
- Idempotent complaint processing.
- Explainability metadata persistence.
- Pagination support for enrichment retrieval.

### Changed

- Improved complaint enrichment workflow.
- Refined API response handling.
- Updated service architecture to support future NLP expansion.

### Fixed

- Removed ORM relationship coupling between `Complaint` and `ComplaintEnrichment`.
- Resolved SQLAlchemy mapper initialization issue.
- Fixed AsyncSession concurrency caused by parallel repository calls.

### Verified

- Docker Compose startup.
- Service health endpoints.
- Swagger/OpenAPI documentation.
- Complaint enrichment API.
- Database persistence.
- Runtime logs.
- Unit and integration tests.

---

# Previous Milestones

## Phase 1 – Foundation

### Completed

- Project scaffolding.
- Shared infrastructure.
- Configuration management.
- Logging framework.
- Docker environment.

---

## Phase 2 – Data Layer

### Completed

- Database architecture.
- SQLAlchemy models.
- Alembic migrations.
- Repository layer.

---

## Phase 3 – Ingestion Layer

### Completed

- Complaint ingestion pipeline.
- Validation.
- Persistence.
- Duplicate detection.
- API endpoints.

---
