# Phase 13 Architecture — Production Hardening

**Status:** PHASE 13 ARCHITECTURE — FROZEN. READY FOR IMPLEMENTATION. All six architecture decisions (AD-1 through AD-6) are resolved. No unresolved architecture decision, no implementation-blocking architecture question, and no batch blocked by architecture ambiguity remain.

**Date:** 2026-08-14 (AD-2 resolved same-day, after architecture-review follow-up)

**Scope boundary:** Phases 1–12 are complete and are not reopened by this document. This architecture strengthens the boundaries Phases 1–12 already established; it does not redesign domain logic, intelligence engines, the Gateway/BFF pattern, Phase 11 observability, or Phase 12 Copilot orchestration.

---

## 1. Executive Summary

This document is the authoritative architecture for Phase 13 (Production Hardening), produced by a repository-grounded review of a proposed design against the actual implementation of Phases 1–12. The review verified every claim against code — Gateway routes, ORM models, Alembic migrations, Dockerfiles, `docker-compose.yml`, the frontend API client, and every relevant ADR — rather than against documentation claims about that code.

The proposed architecture passed review **with one required correction** (AD-6: the originally proposed cross-origin HttpOnly-cookie design would silently fail under this platform's actual frontend/Gateway origin setup — corrected to a same-origin design) and, at initial review, one sub-decision left explicitly open (AD-2: whether "hardened Compose" modifies the existing dev-oriented `docker-compose.yml` in place or introduces a production override file). **That sub-decision is now resolved**: Phase 13 introduces a separate `docker-compose.prod.yml` production configuration, leaving `docker-compose.yml` as the unchanged development configuration (see §20, §29). Every other proposed element — Gateway-owned identity, RBAC, internal service trust, recommendation decision attribution, Copilot ownership/retention, CI, backup/restore, and investigation parallelization — is compatible with the repository and every frozen decision it was checked against, with several genuinely missing details (principal propagation, cross-service FK precedent, migration sequencing) resolved directly in this document.

**All six architecture decisions (AD-1 through AD-6) are now resolved. No unresolved architecture decision, implementation-blocking question, or pending team decision remains anywhere in this document.**

## 2. Phase 13 Objective

Production-harden the existing platform without redesigning its domain architecture. Phase 13 adds identity, authorization, and operational maturity on top of Phases 1–12's already-complete intelligence pipeline; it does not replace or reopen any of it.

## 3. Scope

- Gateway-owned user identity, authentication, and RBAC (AD-1, AD-6, §7–§11).
- Internal service-to-service trust for genuine internal mutation boundaries, and principal propagation for the two downstream services that need authenticated identity (AD-5, §12–§13).
- Recommendation decision attribution and an append-only decision history (AD-3, §14–§15).
- Copilot conversation ownership and a three-way retention model (AD-4, §16–§17).
- Secrets/configuration hardening, Docker/runtime hardening, CI quality gates, database backup/restore (§18–§21).
- Investigation aggregator concurrency correction (§22), previously identified as a real latency pressure point.
- A final, honest, twelve-stage synthetic-data validation exercise, run only once every stage — including authentication/authorization — can be truthfully exercised (§27).

## 4. Non-Goals

Unless repository evidence proves otherwise (none did), Phase 13 explicitly excludes: a new authentication microservice, OAuth/SSO/MFA/social login, Kubernetes/Helm, a service mesh, mTLS, SPIFFE, Kafka/RabbitMQ/Redis, a generic retry framework or circuit breaker, HA/multi-region, cloud migration, new intelligence engines, any Copilot mutation tool or arbitrary HTTP access, a generic enterprise audit platform, and any redesign of Phase 11 observability or Phase 12 Copilot orchestration. None of Phase 1–10's completed domain architecture is reopened.

## 5. Existing Architecture Baseline (verified, not assumed)

- **ARCH-001/ARCH-002**: modular service-based monorepo, one shared PostgreSQL instance, logical (not physical) service ownership of entities.
- **DATA-001/DATA-002**: referential integrity enforced at the database level across service boundaries without ORM coupling; every service owns its own SQLAlchemy models; no service imports another service's ORM classes; services define minimal local read models when they need another service's already-persisted data.
- **Gateway (`gateway_service`)**: the platform's sole public API boundary (`/api/v1/*`), a pure BFF/aggregator today — 9 routes total (verified exhaustively, §6), zero persistence, zero auth code of any kind.
- **Migrations**: one shared directory (`backend/migrations/versions/`), one linear Alembic chain, current head `b3c8e5a1f204`, no branching, ever.
- **Phase 11 observability**: structured logging, `X-Request-ID` correlation, Prometheus HTTP metrics, OpenTelemetry tracing, two verified Grafana dashboards, an allowlist-based (not blocklist-based) log-redaction discipline — all real, all verified against genuine outages, none touched by this document.
- **Phase 12 Copilot**: `copilot_service`, seven structurally read-only tools (COPILOT-001), conversation persistence with no owner/retention field (COPILOT-002), a frozen `CopilotResponse` contract — none touched except the two additive columns/routes this document specifies.
- **REC-003**: recommendation decisions persist without attribution, by deliberate design, explicitly anticipating this Phase 13 follow-up.

## 6. Whole-Project Compatibility Matrix

| Phase | Existing responsibility | Phase 13 interaction | Compatibility | Potential conflict | Required action |
|---|---|---|---|---|---|
| 1 — Foundation | Shared infra, Docker, project structure | Gateway gains DB dependency; Docker hardened | Compatible | None | Add `alembic.ini` to `gateway_service`'s Dockerfile; add DB engine/session wiring |
| 2 — Data modeling | Complaint/operational data model | None | Compatible | None | None |
| 3 — Ingestion | `ingestion_service` | None (not Gateway-exposed today; unaffected) | Compatible | None | None |
| 4 — NLP | `nlp_service` | Copilot's read-only NLP evidence tool unaffected | Compatible | None | None |
| 5 — Anomaly/Incident | `anomaly_service` | None | Compatible | None | None |
| 6 — Root Cause | `root_cause_service` | RBAC matrix notes no confirm/reject/refresh routes exist yet (deferred, Step 7.X G-04) | Compatible | None — nothing to protect that doesn't exist | Re-run RBAC mapping if/when G-04 ships |
| 7 — Business Impact | `business_impact_service`, event fan-out | Its two `/internal/events/*` receivers (on recommendation/evaluation services) gain a shared-secret check (AD-5) | Compatible | None | Add internal-secret header to the publisher's outbound calls |
| 8 — Evaluation | `evaluation_service`, out-of-band observer | Its `/internal/events/*` route gains the same shared-secret check | Compatible | None | Same as above |
| 9 — Recommendation | Decision engine, REC-002/REC-003 | Gains `decided_by` + history table (AD-3) | Compatible — REC-003 explicitly anticipated this | None | Sequence migration after AD-1's `users` table exists |
| 10 — Frontend/Gateway | 5 workspaces, BFF, Step 7.X | Auth UI, session handling, RBAC-aware UI hiding (advisory only) | Compatible, with one required correction | AD-6's original cross-origin cookie design was broken as proposed | Restore same-origin frontend↔Gateway path (§9) |
| 11 — Observability | Logging/metrics/tracing/Grafana | Auth events logged via existing structured logger; no new stack | Compatible | High-cardinality label risk if done carelessly | Follow §23's explicit labeling rules |
| 12 — Copilot | Read-only tools, conversation persistence | Ownership column + principal header + new DELETE route | Compatible — COPILOT-002 explicitly anticipated this | None to the tool boundary; new API surface only | Add owner_id, DELETE route; zero change to the 7 tools |

**Architecture Review Board decisions**: ARB-001 through ARB-008 concern platform identity, long-term lifecycle vision, Business Impact genericity, presentation-layer adaptation, organizational knowledge, the evidence chain, Incident-as-central-object, and stage-specific confidence — none are touched by Phase 13; verified no conflict.

**Product Experience Guide**: verified compatible (§26). One informational, non-blocking note: Administration's illustrative UI copy (`UserAccessManagement.tsx`, `PlatformGovernance.tsx`) currently describes "single sign-on via the organization's identity provider" — that copy is explicitly self-labeled illustrative/placeholder (not real data), and Phase 13's actual design (project-owned password auth, not SSO) does not match it. Non-blocking; flagged for future copy reconciliation if that Administration surface is ever wired to real data.

**Final synthetic-data validation plan**: compatible and, in fact, the reason this document exists — see §27.

### 6a. Targeted Consistency Check — AD-2 Resolution (Separate Production Compose)

Performed after AD-2 was resolved (§20), scoped narrowly to whether a separate `docker-compose.prod.yml` introduces any contradiction — not a re-run of the full Phase 13 review.

| Area | Verified | Result |
|---|---|---|
| Frontend API origin/proxy behavior | `vite.config.ts:20-25` proxies `/api` → `gateway_service:8000` by Compose service name, not `localhost` | Compatible — same proxy pattern works unchanged once layered under a production reverse-proxy/serving strategy (§9) |
| Gateway URL configuration | `GatewaySettings` (§7) addresses every downstream service by Compose service name (`http://recommendation_service:8006`, etc.), never `localhost` | Compatible — identical in both configurations by construction |
| Service-to-service networking | All 8 backend services already reachable only by Compose DNS name, no host port | Compatible — the production configuration's network segmentation (§20) narrows *which* other containers can reach them, without changing *how* they're addressed |
| PostgreSQL connectivity | `POSTGRES_HOST=postgres` (`.env.example:5`), addressed by service name everywhere | Compatible — unaffected by removing the host port mapping in the production configuration |
| Prometheus scrape targets | `infrastructure/observability/prometheus/prometheus.yml:15-58` — every job targets a Compose service name/port (`gateway_service:8000`, etc.), zero `localhost` targets except Prometheus's own self-scrape | Compatible — no scrape-config change needed for either compose configuration |
| Loki / Promtail | Promtail mounts the host Docker socket/log directory and ships to `loki` by service name | Compatible — unaffected by the public/internal network split (Promtail and Loki both belong on the internal network) |
| OTel Collector / Tempo | `OTLP_EXPORTER_ENDPOINT=otel-collector:4317` (`.env.example:31`), Tempo addressed by service name in Grafana's datasource config | Compatible — same reasoning |
| Grafana | `infrastructure/observability/grafana/provisioning/datasources/datasources.yml:15,23,30` — all three datasource URLs use Compose service names (`http://prometheus:9090`, etc.) | Compatible — no datasource change; Grafana's own host exposure/credential rotation is a production-configuration concern only (§19) |
| Copilot | `copilot_service`'s Gateway route and internal downstream calls are already Compose-service-name-addressed | Compatible — no change from the compose split; ownership/retention (AD-4) is orthogonal to which compose file is used |
| Persistent volumes | `postgres_data` and the four observability volumes are named Docker volumes, not bind mounts | Compatible — both configurations can reference the same named volumes; no data-loss or divergence risk from running either configuration against the same volume set |
| Health / readiness | `/health`/`/health/ready` are implemented in application code (`backend/shared/observability/health.py`), not compose-file-specific | Compatible — identical behavior regardless of which compose file started the container |
| Final validation startup procedure | The twelve-stage synthetic-data validation (§27) can run against either configuration; running it against the production configuration is the more representative choice once Phase 13 implementation is complete | Compatible — no procedural contradiction |

**No contradiction was found.** The separate-production-compose decision is confirmed compatible with Phases 1–12, the Product Experience Guide, and the final synthetic-data validation plan.

## 7. Authentication Architecture

Per **AD-1** (`docs/DECISIONS.md`), authentication is a `gateway_service`-owned capability, matching `ARCHITECTURE.md` §5/§D/§11's original (never-implemented, never-contradicted) intent. `gateway_service` gains:

- A password-hash-based login flow (`POST /api/v1/auth/login`) issuing a short-lived JWT.
- Server-side JWT validation on every authenticated route via a FastAPI dependency (the platform's first `Depends(get_current_user)`-shaped code).
- No password reset, email verification, MFA, OAuth, SSO, or social login — none is justified by any repository evidence or product requirement found during this review; all are non-goals (§4) unless a future decision reopens this.

```
Browser
  |
  |  HttpOnly cookie (same-origin, see §9)
  v
Gateway (gateway_service)
  |-- Authentication  (verify password hash, issue JWT)
  |-- Authorization    (role check per route, §11)
  `-- Identity persistence (users / roles / user_roles)
          |
          v
      PostgreSQL (shared instance, ARCH-002)
```

Downstream services never validate a JWT themselves (§12–§13) — they trust a Gateway-attested header, keeping token logic inside one boundary per AD-1's explicit goal.

## 8. PostgreSQL Identity Model

Owned exclusively by `gateway_service`, in the shared Postgres instance, migrated through the existing single linear Alembic chain (current head `b3c8e5a1f204` — a new identity migration attaches after it).

```
users
  id               UUID PK
  email            citext/varchar, unique, not null
  password_hash    text, not null        -- bcrypt/argon2, never plaintext
  is_active        boolean, not null, default true
  created_at       timestamptz, not null
  updated_at       timestamptz, not null
  last_login_at    timestamptz, nullable

roles
  id               UUID PK
  name             varchar, unique, not null   -- 'viewer' | 'operator' | 'admin'
  description      text, nullable

user_roles
  user_id          UUID, FK -> users.id
  role_id          UUID, FK -> roles.id
  PRIMARY KEY (user_id, role_id)
```

Verified no naming collision with any existing table. `is_active` (soft-deactivation, not hard delete) matches the platform's existing convention of state flags over destructive deletes (e.g., `ANOMALY-001`'s active/resolved lifecycle). This table set is the one and only place `decided_by` (§14) and `owner_id` (§16) foreign-key against, via the DATA-001-precedented cross-service database-level FK pattern (raw Alembic constraint, no ORM import).

## 9. JWT / Cookie / CORS / CSRF Security Model

**This section supersedes the originally proposed cross-origin design — see AD-6 for the full contradiction and correction.**

Verified today: frontend serves at `http://localhost:3000`, Gateway at `http://localhost:8000` — different origins. `docker-compose.yml:237` currently forces the frontend to call the Gateway's absolute cross-origin URL, and the frontend's `fetch`-based client (`client.ts:96-105`) sets no `credentials` option. Under this configuration, an HttpOnly cookie set by the Gateway would never be returned by the browser on any frontend request — the design as originally proposed does not work.

**Corrected design**: frontend and Gateway are same-origin in every environment.
- **Dev/Compose**: use `vite.config.ts`'s already-existing `/api` → `gateway_service:8000` proxy (`vite.config.ts:20-25`); stop overriding `VITE_API_BASE_URL` to an absolute cross-origin URL in `docker-compose.yml`.
- **Production (`docker-compose.prod.yml`, AD-2 resolved)**: an equivalent same-origin path is implemented in the production configuration (e.g., the Gateway serving the built frontend bundle, or a shared reverse proxy in front of both) — see §20.

With same-origin restored:
- **HttpOnly**: yes, always — frontend JavaScript never reads the token.
- **Secure**: yes in any non-`localhost` deployment (required for `SameSite=Lax`/`None` cookies over HTTPS; `localhost` gets browser leniency in dev).
- **SameSite**: `Lax` — sufficient once same-origin, avoids `SameSite=None`'s broader cross-site exposure and its hard HTTPS requirement.
- **CORS**: `allow_origins` stays an explicit allowlist (today: `http://localhost:3000,http://localhost:5173`, from `CORS_ALLOWED_ORIGINS`) — never a wildcard; `allow_credentials=True` is already set (`main.py:48-54`) and remains correct now that it's paired with a real cookie.
- **CSRF**: `SameSite=Lax` blocks the cookie on cross-site requests, including classic form-triggered CSRF; combined with every mutating Gateway route already requiring `application/json` (true today for the recommendation-decision PATCH and will be true for the new Copilot DELETE), the simple/no-preflight form-based CSRF vector is already closed. No separate CSRF token is required for the prototype. A double-submit token remains a documented, deferred (§20) hardening option only if a genuinely cross-origin client is ever introduced.
- **Logout**: `POST /api/v1/auth/logout` clears the cookie via `Set-Cookie` with immediate expiry. No server-side token blocklist — token lifetime is short enough that expiry is the primary defense (kept deliberately simple; a blocklist is a future item if evidence ever shows token misuse between issuance and natural expiry).
- **Expiry/invalid-token behavior**: any authenticated route with an expired or invalid token returns `401` through the Gateway's existing standardized error envelope (`code`/`message`/`requestId`/`details`, Phase 10 Step 7 convention) — never a silent success, never a bespoke redirect baked into the API layer. The frontend interprets `401` and prompts re-authentication, consistent with the Product Experience Guide's "communicate honestly, never fail silently" principle (§26).

## 10. Authentication API

```
POST /api/v1/auth/login    -- verify credentials, issue HttpOnly cookie
POST /api/v1/auth/logout   -- clear cookie
GET  /api/v1/auth/me       -- return AuthenticatedUser (user_id, email, roles) for the current session
```

A refresh endpoint is **not** added — no repository or product evidence justified it during this review; short-lived tokens plus a full re-login on expiry is sufficient for this prototype's traffic and session-length expectations. Revisit only if a future decision determines session length must exceed what's comfortable for a single non-refreshing token. Fits the existing Gateway routing convention exactly (`app.include_router(..., prefix="/api/v1")`, `main.py:70-75`) — a fourth router module (`auth.py`) alongside the six that already exist.

## 11. RBAC Model

Initial roles, checked against the 9 actual Gateway routes (verified exhaustively — no invented endpoints):

- **viewer** — read-only access to every GET route.
- **operator** — viewer + the one mutating domain route that exists today (`PATCH /recommendations/{id}/decision`) + Copilot (`POST /copilot/messages`, `DELETE /copilot/conversations/{id}` on their own conversations).
- **admin** — operator + reserved for future administrative mutation capability. **Honest finding**: no administrative mutation route exists in the Gateway today (`/api/v1/administration/*` is 100% read-only — Platform Overview and Intelligence Configuration are both `GET`). `admin` currently has zero exclusive capability beyond `operator`. It is kept as a reserved role for forward compatibility (e.g., a future real User & Access Management backend) rather than removed, but this document records honestly that it does nothing distinct yet — not fabricated scope.

## 12. Permission Matrix

| Route | Method | Capability | Required role | Read/Write |
|---|---|---|---|---|
| `/api/v1/dashboard` | GET | Dashboard aggregate view | viewer | Read |
| `/api/v1/investigations/{incident_id}` | GET | Investigation aggregate view | viewer | Read |
| `/api/v1/recommendations/{recommendation_id}` | GET | Recommendation read | viewer | Read |
| `/api/v1/recommendations/{recommendation_id}/decision` | PATCH | Record a recommendation decision | operator | Write |
| `/api/v1/analytics/trends` | GET | Trend analytics | viewer | Read |
| `/api/v1/administration/overview` | GET | Platform health overview | viewer | Read |
| `/api/v1/administration/intelligence-configuration` | GET | Read-only engine configuration | viewer | Read |
| `/api/v1/copilot/messages` | POST | Copilot query (own conversations) | operator | Write (persists a message) |
| `/api/v1/copilot/conversations/{id}` (new, AD-4) | DELETE | Delete own conversation | operator (owner-only) | Write |
| `/api/v1/auth/login`, `/logout` | POST | Session lifecycle | unauthenticated → authenticated | — |
| `/api/v1/auth/me` | GET | Current principal | any authenticated role | Read |
| `/health` | GET | Liveness | unauthenticated (operational, not user-facing) | Read |

**No route exists for Root Cause confirm/reject/refresh** — those actions were explicitly deferred at Step 7.X (G-04) and never built. This document does not invent a role mapping for a capability that doesn't exist; re-run this matrix if/when G-04 ships. **Observability surfaces** (Grafana, Prometheus) are separate systems with their own (currently weak-default) auth, outside this RBAC model's scope — see §19 for their hardening treatment. Frontend UI role-based hiding is advisory UX only; the Gateway's own role check on each route above is the sole authorization authority, per this review's explicit instruction that frontend visibility is never authorization.

## 13. Internal Service Trust Model

Two distinct trust domains, per AD-5:

```
USER TRUST                          SERVICE TRUST
Browser                             gateway_service / business_impact_service
  |  HttpOnly cookie, same-origin      |  X-Internal-Secret header
  v                                    v
Gateway                             recommendation_service / evaluation_service /
  |  validates JWT, resolves           copilot_service
  |  AuthenticatedUser                 |  trusts header presence + secret match
  v                                    v
Authorization (role check)          services never parse a JWT
```

Gateway → downstream read calls (dashboard, investigation, recommendations, analytics, administration aggregators) and `copilot_service` → downstream read calls (the seven tools) are **not** given the internal secret — they remain protected by network topology alone (no host-published port), consistent with the Step 0 audit's explicit instruction to protect genuine internal mutation boundaries, not arbitrary internal functions.

## 14. Internal Trust Matrix

| Caller | Target | Internal endpoint | Current transport | Current trust | Proposed trust | Credential source | Why protection is required |
|---|---|---|---|---|---|---|---|
| `business_impact_service` | `recommendation_service` | `POST /internal/events/business-impact-completed` | `httpx.AsyncClient.post`, concurrent fan-out | Network topology only (no host port) | `X-Internal-Secret` header, `Depends()`-validated | Env-injected shared secret | Genuine mutation endpoint (triggers recommendation generation); one misconfigured port mapping fully exposes it today |
| `business_impact_service` | `evaluation_service` | `POST /internal/events/business-impact-completed` | Same as above, independent fan-out branch | Same | Same | Same | Same |
| `gateway_service` | `recommendation_service` (+7 others) | Public-shaped read routes (`GET /recommendations/{id}`, etc.) | `httpx.AsyncClient`, 5s timeout | Network topology only | **Unchanged** (no secret added) | — | These are read-only aggregation calls, not internal mutation boundaries — adding protection here is scope creep beyond what's justified |
| `gateway_service` | `recommendation_service` | `PATCH /recommendations/{id}/decision` | `httpx.AsyncClient.patch` | Network topology only | + `X-Authenticated-User-Id` header (principal propagation, AD-3) | Gateway-attested, carried alongside the internal secret | `decided_by` must be trustworthy, not client-suppliable |
| `gateway_service` | `copilot_service` | `POST /copilot/messages`, new `DELETE /copilot/conversations/{id}` | `httpx.AsyncClient` | Network topology only | + `X-Authenticated-User-Id` header (principal propagation, AD-4) | Same | `owner_id` must be trustworthy, not client-suppliable |
| `copilot_service` | `anomaly_service`/`root_cause_service`/`business_impact_service`/`recommendation_service`/`nlp_service` | Each service's own public-shaped `GET` routes (7 tools, COPILOT-001) | `httpx.AsyncClient.get` only (structurally no mutating verb, `downstream.py` exposes no POST/PATCH/PUT/DELETE helper) | Network topology only | **Unchanged** | — | Already structurally read-only by construction, verified via source-level test assertions (`test_tool_registry.py:102,109`) |

## 15. Recommendation Decision Attribution

See AD-3 in full. Summary: `RecommendationModel` gains `decided_by` (nullable UUID FK → `gateway_service.users.id`). The `PATCH .../decision` handler populates it from the Gateway-attested principal header (§13), never the request body — `RecommendationDecisionPatchRequest` gains no new client-facing field. Domain semantics (`RecommendationDecision` enum values, scoring, category rules) are untouched.

## 16. Recommendation Decision History

`recommendation_decision_history` — new, service-owned, append-only table in `recommendation_service`:

```
recommendation_decision_history
  id                UUID PK
  recommendation_id UUID, not null (no FK to recommendations required for the review's purposes, but recommended for integrity)
  decision          same enum as recommendations.decision
  decision_note     text, nullable
  actor_id          UUID, FK -> gateway_service.users.id, nullable
  created_at        timestamptz, not null, server-default
```

Written on every successful `PATCH .../decision` call, in the same transaction as the overwrite to `recommendations.decision/decision_note/decided_at` — never instead of it. Not exposed as a generic audit UI or exported anywhere by this document; it exists to answer "what did this recommendation's decision look like at each point in time," nothing broader.

## 17. Copilot Ownership

See AD-4 in full. `copilot_conversations.owner_id` (nullable UUID FK → `gateway_service.users.id`), populated from the Gateway-attested principal header on every conversation create/continue. `_resolve_conversation()` (`conversation_service.py:88-117`) gains an ownership check: a caller may only resolve a conversation whose `owner_id` matches their own `user_id` (or `owner_id IS NULL`, for pre-Phase-13 orphaned rows, treated as inaccessible until a future decision addresses them — not silently granted to the first caller who guesses the UUID). Admin does not receive an override. The seven Copilot tools (COPILOT-001) are unmodified.

## 18. Copilot Retention / Deletion

Three-way split, per AD-4:
1. **Technical mechanism**: optional, configurable age-based purge job on `last_message_at`; requires a new index on that column, added in the same migration as the purge job itself.
2. **Prototype default**: mechanism ships disabled — preserves COPILOT-002's existing "no automatic expiry" posture unless explicitly turned on.
3. **Future business/compliance policy**: actual retention duration is explicitly out of scope for this document — a real compliance decision, not an engineering default.

User-initiated deletion (`DELETE /api/v1/copilot/conversations/{id}`, owner-only) ships regardless of whether the automatic-purge mechanism is enabled.

## 19. Secrets and Configuration

- No weak/default credential ships in `.env.example` for production use; the file's current `POSTGRES_PASSWORD=postgres`/`GF_SECURITY_ADMIN_PASSWORD=admin` defaults are explicitly documented as dev-only and must be rotated by whatever deployment-time secret injection Phase 13's Docker hardening introduces (§20).
- No cloud secret manager is introduced — not justified by AD-2's single-host Compose target; runtime secrets continue to be injected via `env_file`, per the existing convention, just with real (non-default) values at deploy time.
- The JWT signing secret (a new secret this document introduces) follows the identical env-injection convention as every existing secret (`POSTGRES_PASSWORD`, `LLM_API_KEY`) — no special-cased handling.
- Grafana and Prometheus (§14 of the Step 0 audit) keep their own existing, separate auth postures — Grafana already has its own admin login (weak default, needs rotation per the same rule above); Prometheus has none today and should gain network-level protection via §20's network segmentation rather than a bespoke auth integration, which Phase 11 (`OBS-002`/Phase 11 closure) already correctly scoped as out of band from platform auth.

## 20. Docker / Runtime Hardening

Verified current state: single flat bridge network (no `networks:` key), every backend Dockerfile runs as root (no `USER` directive, confirmed absent across all 9), `frontend/Dockerfile` runs `npm run dev` as its `CMD` (no multi-stage build), `postgres` is host-published at `5432` with the weak default credential, no CI, no backup/restore.

**AD-2 resolution (deployment split)**: `docker-compose.yml` remains the development configuration, unmodified — bind mounts, `--reload`, and the Vite dev server stay exactly as they are today, so no contributor's local workflow changes because of this document. Phase 13 introduces a separate `docker-compose.prod.yml` production configuration (a Compose override or a self-contained file — a packaging detail left to implementation, not architecture) implementing every item below. Both configurations represent the same 15-service topology (same service names, same internal/external port split) unless a documented, architecture-approved difference is introduced; the production configuration changes only *how* services are built and run, never *what* the platform does.

Required hardening, implemented in `docker-compose.prod.yml` only, all within AD-2's "no Kubernetes/mesh/mTLS" boundary:
- **Frontend**: multi-stage Dockerfile — build stage (`npm run build`, already scripted but never invoked) + a minimal static-serve stage, replacing the dev-server `CMD`. Same-origin path to the Gateway (§9) is implemented here (e.g., the Gateway serving the built bundle, or a shared reverse proxy in front of both) — the development configuration keeps using the existing Vite proxy (`vite.config.ts:20-25`) unchanged.
- **Backend services**: no `--reload`, no `./backend:/app/backend` source bind mount — the image's own `COPY`ed source is authoritative in the production configuration; the development configuration is unaffected.
- **Postgres**: the production configuration does not publish `postgres:5432` to the host (or binds it to `127.0.0.1` only if host-side `psql` access is genuinely needed for operations); rotate the default credential for any real deployment. The development configuration's host-published port is unchanged (a real local-development convenience, not a production concern).
- **Network segmentation**: in the production configuration, two Compose-native networks — `public` (gateway_service, frontend) and `internal` (the 8 backend services + postgres), with `gateway_service` joining both. Plain Compose functionality, not a mesh; directly closes the "any container reaches any other container" finding.
- **Non-root execution**: add a `USER` directive to every Dockerfile where feasible, applied in the production configuration; the development configuration's bind-mount + `--reload` workflow may still require root or host-UID-aligned execution locally, which the production configuration's lack of bind mounts avoids entirely — no UID-alignment problem exists once source is baked into the image rather than mounted.
- **Restart policy**: already present (`restart: unless-stopped`) on every service except `postgres` in the base file — add it there too, inherited by both configurations (a base-file fix, not production-only).
- **Migration execution**: today entirely manual (`alembic upgrade head`, no runner container, confirmed — `gateway_service`'s Dockerfile does not currently copy `alembic.ini`). Phase 13 requires `gateway_service`'s Dockerfile to copy `alembic.ini` (matching `ingestion_service`'s existing precedent) so its new identity migrations can run the same manual way every other service's migrations already do, in both configurations — no new migration-runner infrastructure is introduced.
- **Observability**: verified compatible with the production split — `prometheus.yml`, Grafana's datasource provisioning, and every other observability config reference services exclusively by their Compose service name (e.g. `gateway_service:8000`, `http://prometheus:9090`), never `localhost` or a dev-only address, so no observability configuration changes when the production topology is layered on (see §6a).

## 21. CI Quality Gates

No CI exists today (confirmed absent — no `.github/workflows`, no `.gitlab-ci.yml`, no pre-commit/husky config anywhere). Phase 13 introduces a CI pipeline using only tools the repository already has: pytest (backend, 145+ existing test files across 9 services), Vitest (frontend, 43+ existing test files), `tsc` (typecheck, already scripted), the repository's existing lint tooling (already invoked manually per every phase-closure verification section in `PROJECT_STATUS.md`), the frontend production build (`npm run build`, scripted but never invoked — §20 makes it load-bearing for the first time), and `docker compose config` validation (already used manually per Phase 10 Step 7 closure evidence). No new CI stack, framework, or tool is introduced — this is wiring existing, already-working tooling into automation for the first time.

## 22. Database Backup / Restore

No backup/restore mechanism exists today (confirmed absent — no `pg_dump`, no cron, no documented procedure anywhere). Phase 13 introduces a practical, prototype-appropriate procedure: a scheduled (or manually-triggered, for the prototype) `pg_dump` of the shared Postgres instance to a mounted volume or bind-mounted host directory, a documented restore procedure (`pg_restore` against a fresh `postgres` container), and a test execution verifying a restored database passes the platform's own health checks. No HA database architecture (replication, failover) is introduced — not justified by this single-instance, single-host deployment target.

## 23. Observability Integration

Reuses the existing Phase 11 stack in full — no new logging, metrics, tracing, or dashboard infrastructure. Authentication/authorization events (login success, login failure, logout, token-expiry rejection) are logged through the existing structured JSON logger (`backend/shared/logging/logger.py`), participate in the existing `X-Request-ID` correlation model, and may appear in traces exactly like any other Gateway request — no new telemetry subsystem.

**Explicit prohibitions, honored**: never log passwords, JWTs, cookie values, or `Authorization`/`X-Internal-Secret` header values — the existing allowlist-based (`safe_extra`) logging discipline already structurally prevents this (an allowlist cannot leak a field nobody added to it), and the existing `_FORBIDDEN_SECRET_PATTERNS` test (`test_observability_infrastructure.py:25`) is extended to also cover the new secret vocabulary this document introduces. Never create a Prometheus label from `user_id`, `email`, or `conversation_id` — if auth-failure-rate metrics are wanted, use a bounded label such as `outcome=success|failure`, never a raw identity value. `user_id` may appear as a structured **log field** (not a metric label) via the existing allowlist mechanism, since logs and metrics have different cardinality cost profiles.

## 24. Frontend Integration

No frontend code is modified by this document (out of scope for this review). Architecturally: `AppProviders.tsx`'s own existing doc comment already earmarks itself as the composition point for "a future auth/session... provider" (`AppProviders.tsx:11-14`) — this is the natural, already-anticipated place a session/user context is introduced. `AppShell.tsx` mounts no "current user" concept today; a user menu/session-state display would consume the new provider from there. The shared API client (`client.ts`) needs `credentials` behavior appropriate to the now-same-origin design (§9) and a `401` → re-authentication-prompt handling path. None of this is implemented by this document.

## 25. Product Experience Compatibility

Verified compatible against the Product Experience Guide's own principles: **Calm Software** (session-expiry UX should use hierarchy, not chaos — no jarring modals, no repeated nags); **User Experience Goals** (Confident/In Control/Supported — a re-auth prompt should explain why, not just block); **Trust & Explainability** (session state communicated honestly, never silently failing — matches §9's explicit `401`-over-silent-failure rule); **Cognitive Load Management** (permission-based UI hiding, not show-then-error — though the Gateway's role check remains the sole authorization authority regardless of what the UI hides, per §12). One informational note carried from §6: `UserAccessManagement`/`PlatformGovernance`'s illustrative copy currently describes SSO, which doesn't match this document's project-owned-password design — non-blocking, flagged for future reconciliation only if that Administration surface is ever wired to real data.

## 26. Phase 1–12 Boundary Analysis

See the compatibility matrix (§6) for the full phase-by-phase analysis. Summary: no phase's domain logic, persistence ownership, or API contract is altered. The only genuinely new architectural capability added to any existing service is `gateway_service` gaining its own persistence (§7–§8) — everywhere else, this document adds additive columns, new routes, or a header convention on top of already-existing infrastructure.

## 27. Final Synthetic-Data Validation

The Step 0 audit found the pipeline's stages through Copilot/Evaluation/Observability already real and phase-closure-verified, but structurally unable to include Authentication/Authorization in an honest "final full-pipeline validation" — there was nothing there to validate. This document is what closes that gap. Once Phase 13 is implemented (not before), a full twelve-stage synthetic-data run — ingestion → NLP → anomaly → incident → root cause → business impact → evaluation → recommendation → analytics → Copilot → observability → authentication/authorization — can be executed and reported honestly, distinguishing tested-successfully / partially-tested / unavailable / known-limitations for every stage, with no fabricated result for any of them. This exercise is explicitly sequenced **after** all Phase 13 implementation batches (§30), not before.

## 28. Security Threat / Failure Scenarios

| Scenario | Mitigation in this design |
|---|---|
| Stolen/leaked JWT cookie | `HttpOnly` (JS can't read it), short expiry, `Secure` in production |
| CSRF via a third-party site | `SameSite=Lax` + JSON-only mutating routes (no simple-form CSRF vector) |
| Cross-origin cookie theft/misdelivery | Closed structurally by making frontend/Gateway same-origin (§9) rather than relying on `SameSite=None` discipline |
| Internal event route called from outside the Docker network | Currently possible if a port were ever accidentally published; closed by the `X-Internal-Secret` check (§13–§14), independent of network topology |
| Spoofed `decided_by`/`owner_id` from a malicious client | Both are populated only from the Gateway-attested principal header, never the request body (§15, §17) |
| Weak default credentials reaching a real deployment | `.env.example` defaults explicitly flagged as dev-only; rotation required as part of Docker hardening (§19–§20) |
| Compromised low-privilege container (e.g., an observability sidecar) pivoting to Postgres | Reduced, not eliminated, by network segmentation (§20) — full elimination would require mTLS/mesh, explicitly rejected as premature for this deployment target (AD-2) |
| Auth failure/success flooding logs or metrics with high-cardinality identity data | Structural prevention via the allowlist logging discipline and the explicit no-identity-as-metric-label rule (§23) |

## 29. Implementation Constraints

- **Migration ordering**: AD-1's `users`/`roles`/`user_roles` migration must land and run before AD-3's `decided_by` FK migration or AD-4's `owner_id` FK migration — both reference `users.id`.
- **Gateway persistence is new**: `gateway_service` needs DB engine/session wiring (matching `backend/shared/database/database.py`'s existing pattern) and `alembic.ini` copied into its Dockerfile (matching `ingestion_service`'s existing precedent) — this is real, if bounded, new infrastructure work, not a trivial column add.
- **Investigation aggregator concurrency (§22 of the Step 0 audit, carried forward here)**: before parallelizing the two currently-sequential essential calls (`investigation_aggregator.py:68,77`), implementation must verify whether the root-cause fetch depends on data *returned by* the incident fetch, or only shares the same `incident_id` input already available to the caller. If it's the latter (evidence suggests this, but was not exhaustively confirmed by this review), the two calls can be safely gathered concurrently, preserving existing failure semantics (incident 404 still propagates as investigation 404) and evidence ordering (unaffected — ordering was presentational, not causal).
- **Docker/runtime hardening (AD-2, RESOLVED)**: implemented entirely within a new `docker-compose.prod.yml` production configuration; `docker-compose.yml` remains the unmodified development configuration. This is no longer an open question — see §20 and §6a for the full resolution and its compatibility verification. Batch 10 (§32) is unblocked.

**No unresolved architecture decision, implementation-blocking architecture question, or pending team decision remains in this document.**

## 30. Explicitly Deferred Work

Password reset, email verification, MFA, OAuth/SSO/social login, a refresh-token endpoint, Kubernetes/Helm, a service mesh, mTLS/SPIFFE, a message broker, Redis/caching, a generic retry/circuit-breaker framework, HA/multi-region, a double-submit CSRF token (unless a genuinely cross-origin client is later introduced), retroactive attribution of pre-Phase-13 recommendation decisions, retroactive ownership assignment for pre-Phase-13 Copilot conversations, and the actual business/compliance retention duration for Copilot conversations (only the technical mechanism ships in Phase 13, disabled by default).

## 31. Definition of Done

- A user can log in, receive an `HttpOnly` same-origin session cookie, and every previously-anonymous Gateway route now requires a valid, role-appropriate session (per §12's matrix) — `401` on missing/expired/invalid tokens, `403` on insufficient role.
- `RecommendationModel.decided_by` and `recommendation_decision_history` exist, populate correctly from the authenticated principal, and are provably never populated from client-supplied request data.
- `copilot_conversations.owner_id` exists; a user cannot read or continue another user's conversation; `DELETE /api/v1/copilot/conversations/{id}` works for the owner and only the owner.
- The two `/internal/events/*` routes reject requests lacking the internal secret.
- CI runs lint, typecheck, backend + frontend tests, and a real frontend production build on every push, and is green.
- Under `docker-compose.prod.yml`, the frontend Docker image serves a built production bundle, not the Vite dev server — `docker-compose.yml` (development) is unaffected.
- Under `docker-compose.prod.yml`, `postgres:5432` is no longer published to the host (or is host-bound to `127.0.0.1` only) with a rotated, non-default credential — `docker-compose.yml` (development) is unaffected.
- A documented, tested database backup/restore procedure exists.
- No default/weak production credential remains in any shipped configuration.
- The full stack starts successfully via `docker compose -f docker-compose.yml -f docker-compose.prod.yml up` (or an equivalent standalone production file), with every service healthy per its existing `/health`/`/health/ready` checks.
- A full twelve-stage synthetic-data validation report exists, with no fabricated result for any stage.

## 32. Implementation Batch / Step Plan

All eleven batches below are unblocked — no architecture decision remains open.

1. **Batch 1 — CI**: wire existing lint/typecheck/test/build tooling into a pipeline.
2. **Batch 2 — Gateway identity foundation**: `users`/`roles`/`user_roles` migration + models + DB wiring in `gateway_service`.
3. **Batch 3 — Authentication API**: login/logout/me, JWT issuance/validation, same-origin cookie (§9).
4. **Batch 4 — RBAC enforcement**: role checks on all 9 existing Gateway routes per §12's matrix.
5. **Batch 5 — Internal trust**: shared-secret header on the two `/internal/events/*` routes; principal-propagation header from Gateway to `recommendation_service`/`copilot_service`.
6. **Batch 6 — Recommendation attribution**: `decided_by` + `recommendation_decision_history` (depends on Batch 2).
7. **Batch 7 — Copilot ownership**: `owner_id` + ownership check + new DELETE route (depends on Batch 2, Batch 5).
8. **Batch 8 — Database backup/restore**.
9. **Batch 9 — Investigation aggregator concurrency fix** (independent of all identity work; verify the data-dependency question in §29 first).
10. **Batch 10 — Docker/runtime hardening (AD-2)**: introduce `docker-compose.prod.yml` (frontend production build, backend `--reload`/bind-mount removal, network segmentation, non-root execution, Postgres exposure fix, secrets rotation) — `docker-compose.yml` (development) is not modified by this batch.

```
Development Compose (docker-compose.yml)
    remains unchanged throughout every batch above

Production Compose (docker-compose.prod.yml)
    introduced during Batch 10 only
```

Sequenced last, after every batch above:
11. **Final synthetic-data validation** (§27).

## 33. Architecture Decisions / ADR References

AD-1 (Gateway-Owned Project Identity — resolved), AD-2 (Separate Production Docker Compose Configuration — resolved), AD-3 (Recommendation Decision Attribution and History — resolved), AD-4 (Copilot Ownership and Retention Policy — resolved), AD-5 (Internal Service Authentication and Principal Propagation — resolved), AD-6 (Same-Origin HttpOnly JWT Authentication Cookie — resolved) — all recorded in full in `docs/DECISIONS.md`. Referenced existing decisions, unmodified: ARCH-001, ARCH-002, DATA-001, DATA-002, REC-002, REC-003, COPILOT-001, COPILOT-002, OBS-002, ARB-001 through ARB-008.

**PHASE 13 ARCHITECTURE — FROZEN. READY FOR IMPLEMENTATION.** All six architecture decisions are resolved. No unresolved architecture decision, no implementation-blocking architecture question, no pending team decision, and no batch blocked by architecture ambiguity remain.
