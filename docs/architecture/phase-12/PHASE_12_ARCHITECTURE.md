# Phase 12 — AI Copilot
# Final Architecture (Reviewed, Resolved & Frozen)

**Status:** Architecture frozen. No implementation has occurred. No source code, dependencies, Docker Compose, database, or other project documentation was modified to produce this document.
**Date:** 2026-08-13
**Scope boundary:** Phases 1–11 are complete and are not reopened. Phase 13 (Production Hardening — auth/RBAC) is explicitly out of scope and not pulled forward.

This document is the sole authoritative Phase 12 architecture. A prior internal draft was independently reviewed (external review: **PASS WITH CHANGES**, 2 P0 + 5 P1/P2 findings). This document resolves every finding against the actual repository and supersedes the reviewed draft. A new implementation session may begin work from this file alone, without the review or the draft being re-pasted.

---

## 1. Purpose

Add an AI-powered operational Copilot that lets users ask natural-language questions about intelligence the platform has already produced (anomalies, incidents, root causes, business impact, recommendations, trends). The Copilot **interprets and orchestrates**; it does not compute new intelligence.

## 2. Scope

- One new backend service (`copilot_service`, already scaffolded with Phase 11 observability wiring — no business logic yet).
- One new Gateway-routed API surface (`/api/v1/copilot/*`).
- A read-only tool layer inside `copilot_service` that calls existing domain services directly.
- Short-term, service-owned conversation persistence.
- A floating, expandable Copilot panel mounted in the frontend's persistent application shell.
- An agent-level evaluation harness, owned by and scoped to `copilot_service`.

## 3. Non-Goals

Phase 12 does **not** implement: new anomaly/root-cause/business-impact/recommendation intelligence; autonomous remediation; organizational memory, knowledge graphs, or continuous learning; authentication/RBAC or any production access-control policy; production alerting or incident management; a second observability stack; a second domain-evaluation system (Phase 8 remains independent); mutation of any domain entity (including recommendation decisions); a frontend workspace redesign.

---

## 4. Product Experience

The Copilot is secondary to the structured product, not a replacement for it:

```
┌─────────────────────────────────────────────────────────────┐
│ Existing Workspace                                           │
│   Charts / tables / investigation details                    │
│                                         ┌─────────────────┐  │
│                                         │ Copilot         │  │
│                                         │ (compact when   │  │
│                                         │  closed,        │  │
│                                         │  expandable)    │  │
│                                         └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

- Compact/closed by default; expandable on demand; never covers the whole application.
- The user can operate every existing workspace with the Copilot closed — it adds no required interaction.
- Mounted once, application-wide (§14), not per-workspace.

### 4.1 Contextual Entry

Launchable from Dashboard, Investigations, Recommendations, Analytics, or Administration. Context passed in may include only what that workspace's own Context already holds: `workspace`, `incidentId`, `recommendationId`, `filters`, `timeRange`.

**Invariant:** Context is *input* to Copilot, never authority over workspace state. Copilot must never mutate `DashboardContext`, `InvestigationContext`, `RecommendationContext`, `AnalyticsContext`, or `AdministrationContext`. It reads a context snapshot at launch time; it does not subscribe to or write back into any workspace Context.

---

## 5. Actual Service Topology (verified against repository)

`backend/services/` contains exactly these 9 services today — verified directly, not assumed:

```
gateway_service          -- BFF / public API boundary, host-published (8000)
ingestion_service         -- internal-only
nlp_service                -- internal-only
anomaly_service            -- internal-only (owns trends AND incidents/anomalies)
root_cause_service         -- internal-only
business_impact_service    -- internal-only
recommendation_service     -- internal-only
evaluation_service          -- internal-only (Phase 8, independent)
copilot_service              -- internal-only (Phase 12, this document)
```

**There is no `analytics_service` and no `investigation_service`.** These were factual errors in the previously reviewed draft (external review finding F1), corrected here. "Investigation" and "Analytics" are Gateway-side aggregation *code*, not services:

- `gateway_service/app/services/investigation_aggregator.py` composes `anomaly_service` (incident + anomalies), `root_cause_service`, `business_impact_service`, `recommendation_service`, and `nlp_service` into the public `GET /api/v1/investigations/{incident_id}` response.
- `gateway_service/app/services/analytics_aggregator.py` calls `anomaly_service`'s `GET /api/v1/trends` and reshapes it into the public `GET /api/v1/analytics/trends` response.

Phase 12 introduces no new backend service beyond `copilot_service` itself.

---

## 6. High-Level Architecture (corrected)

```
                         ┌─────────────────────┐
                         │      FRONTEND        │
                         │ Existing Workspaces   │
                         └──────────┬───────────┘
                                    │ Public API
                                    ▼
                         ┌─────────────────────┐
                         │      GATEWAY         │
                         │      BFF/API          │
                         │  (unchanged public    │
                         │   routes; adds one     │
                         │   new copilot router)  │
                         └──────────┬───────────┘
                                    │ Copilot API
                                    ▼
                         ┌─────────────────────┐
                         │   COPILOT SERVICE     │
                         │ LangGraph Orchestrator │
                         │ Tool Registry (§10)     │
                         │ LLM Adapter (§16)        │
                         │ Conversation State (§12)  │
                         └──────────┬───────────┘
                                    │ Explicit, registered,
                                    │ read-only tool calls
             ┌──────────────────────┼──────────────────────┬───────────┐
             ▼                      ▼                      ▼           ▼
      anomaly_service        root_cause_service   business_impact_   recommendation_
   (incidents, anomalies,                             service            service
       trends)
             │                                                            │
             └──────────────────────┬────────────────── nlp_service ──────┘
                                  (enrichment summary, via Investigation Tool only)
```

**Critical, non-negotiable boundary (unchanged from the reviewed draft):**

```
Frontend → Gateway → Copilot → read-only tool adapter → authoritative domain service
```

- Copilot **must not** call the public Gateway (no `Copilot → Gateway → Copilot`).
- Gateway remains the sole frontend/public API boundary; its existing 7 routes and 5 aggregators are unchanged by Phase 12.
- `copilot_service` is internal-only in `docker-compose.yml` (no host port), exactly like every domain service except `gateway_service` — consistent with the existing convention (to be applied at implementation time, not by this document).

---

## 7. Copilot Responsibility

**Owns:** natural-language interpretation, tool selection/sequencing, evidence aggregation, conflict presentation, answer synthesis, conversation context, response formatting, LLM interaction.

**Does not own:** anomaly/root-cause/business-impact/recommendation calculations, recommendation decision persistence (write side), dashboard aggregation, any database beyond its own conversation tables. Every domain service remains authoritative for its own domain, unchanged.

---

## 8. Investigation Tool — Resolved Design (F1)

There is no `investigation_service` to call, and Copilot must not call the Gateway. The Investigation Tool is therefore **an independent, Copilot-owned, read-only composition adapter**, conceptually parallel to (but a separate code path from) `investigation_aggregator.py`:

| Property | Value |
|---|---|
| Gateway's existing Investigation aggregator | Remains the sole implementation backing the public `GET /api/v1/investigations/{incident_id}` route. Unchanged by Phase 12. |
| Copilot's Investigation Tool | A second, independent read-only path inside `copilot_service` that calls the same underlying domain services directly. |
| Calls | `anomaly_service` (`GET /api/v1/incidents/{id}`, `GET /api/v1/incidents/{id}/anomalies`), `root_cause_service` (`GET /api/v1/incidents/{id}/root-cause`), `business_impact_service` (`GET /api/v1/business-impact?incident_id=...`), `recommendation_service` (`GET /api/v1/incidents/{id}/recommendations/latest`), `nlp_service` (`GET /api/v1/enrichments/summary`) |
| Constraint | Must not call the public Gateway. Must not introduce a second domain authority (it reads the same records Gateway reads; it computes nothing new). Must not mutate anything. Must not be named or treated as an `investigation_service`. |

**On code sharing (explicit, not deferred):** `backend/shared/` today contains only domain-neutral infrastructure (database, logging, observability, constants) — no existing composition/aggregation primitive that Investigation logic could be extracted into without inventing one. Per this freeze's explicit instruction not to introduce refactoring merely because duplication exists, **no extraction into `backend/shared/` is proposed for Phase 12.** The two independent compositions (Gateway's aggregator, Copilot's tool) are accepted as a conscious duplication: both call the same five endpoints and combine the same fields into a similar shape, but are allowed to drift in *presentation* since Copilot's evidence needs (machine-bound evidence objects) differ from Gateway's frontend-DTO needs. If a future phase finds the two implementations have drifted in *substance* (e.g., what counts as "the incident's current state"), extracting a shared composition primitive should be revisited then, not preemptively now.

---

## 9. Analytics / Trend Tool — Resolved Design (F1)

No `analytics_service` exists. All trend endpoints belong to `anomaly_service`:

```
Copilot → Analytics/Trend Tool → anomaly_service → GET /api/v1/trends
                                                   → GET /api/v1/trends/daily
                                                   → GET /api/v1/trends/categories
                                                   → GET /api/v1/trends/regions
                                                   → GET /api/v1/trends/sentiment
                                                   → GET /api/v1/trends/urgency
```

The tool calls `anomaly_service` directly (never the Gateway's `analytics_aggregator.py`, never the public `/api/v1/analytics/trends` route). It performs no new computation — it passes through `anomaly_service`'s own aggregation, exactly as it exists today.

---

## 10. Exact Tool Registry

Final, repository-verified tool list. Every tool represents a business capability (never a 1:1 raw-endpoint wrapper) and is **read-only**:

1. Recommendation Tool
2. Recommendation Decision Status Tool *(renamed — see §11)*
3. Root Cause Tool
4. Business Impact Tool
5. Investigation Tool (§8)
6. Analytics / Trend Tool (§9)
7. Administration / Configuration Read Tool

No Evaluation tool is introduced (§25 — Phase 8 boundary). No tool wraps a mutation endpoint anywhere (§13 — global invariant).

---

## 11. Recommendation Decision Status Tool — Resolved Design (F2)

**Renamed** from "Recommendation Decision Tool" to **"Recommendation Decision Status Tool"**, resolving the direct self-contradiction the external review found between the tool list and the read-only mandate.

> **Recommendation Decision Status Tool provides visibility into the current persisted recommendation decision state only. It has no decision-writing capability.**

- Reads `decision`, `decision_note`, `decided_at` — fields already present on `GET /api/v1/recommendations/{recommendation_id}`'s existing response (`RecommendationDetailResponse`). No new endpoint is required.
- **Forbidden, explicitly:** `PATCH /api/v1/recommendations/{recommendation_id}/decision`. The tool must never approve, reject, defer, modify, overwrite, create a decision, or assign an actor/owner.
- REC-003's attribution limitation (`docs/DECISIONS.md`) is unaffected and remains true: this tool cannot answer "who decided this," because that data does not exist anywhere in the platform.

---

## 12. Global Read-Only Tool Invariant

**Every Phase 12 Copilot tool is read-only. This is non-negotiable for the whole phase.**

Explicitly excluded from the tool registry, by name, because each is a real, existing mutation endpoint:

| Endpoint | Service | Why excluded |
|---|---|---|
| `PATCH /recommendations/{id}/decision` | `recommendation_service` | Decision mutation (§11) |
| `PATCH /root-causes/{id}/confirm` | `root_cause_service` | State mutation |
| `PATCH /root-causes/{id}/reject` | `root_cause_service` | State mutation |
| `POST /root-causes/{id}/refresh` | `root_cause_service` | Recomputation trigger |
| Any `POST`/`PUT`/`PATCH`/`DELETE` on any service | — | Blanket exclusion |

No generic `http_request()` tool, no arbitrary-URL tool, no direct-database tool, no service-internal execution tool exists or may be added without a new architecture decision.

---

## 13. Exact Tool Contract Matrix

All endpoints below are copied from actual route decorators and response models in the repository (`backend/services/*/app/**`), not invented.

### 13.1 Recommendation Tool

| Field | Value |
|---|---|
| Purpose | Answer questions about a specific recommendation or a bounded set of recommendations |
| Endpoints | `GET /api/v1/recommendations/{recommendation_id}` (`RecommendationDetailResponse`), `GET /api/v1/recommendations?limit=` (`List[RecommendationSummaryResponse]`), `GET /api/v1/incidents/{incident_id}/recommendations/latest` (`List[RecommendationSummaryResponse]`), `GET /api/v1/recommendations/statistics` (`RecommendationStatisticsResponse`) |
| Owning service | `recommendation_service` |
| Read-only | Yes |
| Input parameters | `recommendation_id` (UUID) *or* `incident_id` *or* `limit` (bounded, default/max per existing route) |
| Required context | None mandatory; `incidentId`/`recommendationId` from launch context if present |
| Output DTO | `RecommendationDetailResponse` / `RecommendationSummaryResponse` (`recommendation_id`, `incident_id`, `category`, `priority`, `score`, `action`, `recommendation_rationale`, `priority_rationale` on detail) |
| Evidence fields | `recommendation_rationale`, `priority_rationale` |
| Freshness metadata | None on this DTO (no `created_at`/`updated_at` field exists on `RecommendationSummaryResponse`/`RecommendationDetailResponse` as verified) — Copilot must not claim freshness for recommendation data (§18) |
| Allowed filters | `incident_id`, `limit` (server-bounded) |
| Failure behavior | §22 |
| Forbidden endpoints | `PATCH /recommendations/{id}/decision` |
| **`GET /recommendations/statistics` decision** | **Allowed.** Step 7.X's G-03 deferred this from *frontend Analytics-workspace surfacing* specifically because of conflation risk with the adjacent, still-placeholder "Recommendation Effectiveness" section (`docs/architecture/phase-10/STEP_7X_SCOPE_FREEZE.md`, G-03) — a UI-placement concern that does not apply to a conversational answer. The endpoint returns only aggregate counts/averages (`total_count`, `category_counts`, `priority_counts`, `average_score`), no per-customer or sensitive content. Approved for Copilot use. |

### 13.2 Recommendation Decision Status Tool

| Field | Value |
|---|---|
| Purpose | Report the current decision state of a recommendation |
| Endpoints | `GET /api/v1/recommendations/{recommendation_id}` (same endpoint as §13.1; this tool reads only 3 of its fields) |
| Owning service | `recommendation_service` |
| Read-only | Yes — see §11 |
| Input parameters | `recommendation_id` (UUID) |
| Required context | `recommendationId` (from launch context or prior tool result) |
| Output DTO | Subset of `RecommendationDetailResponse`: `decision`, `decision_note`, `decided_at` |
| Evidence fields | `decision_note` (if present) |
| Freshness metadata | `decided_at` (real field, present when a decision exists; `None` when pending — Copilot must state "no decision recorded yet," never fabricate one) |
| Allowed filters | None (single-recommendation lookup only) |
| Failure behavior | §22 |
| Forbidden endpoints | `PATCH /recommendations/{id}/decision` (absolute) |

### 13.3 Root Cause Tool

| Field | Value |
|---|---|
| Purpose | Explain the identified root cause of an incident |
| Endpoints | `GET /api/v1/root-causes/{root_cause_id}`, `GET /api/v1/root-causes`, `GET /api/v1/incidents/{incident_id}/root-cause` (all `RootCauseResponse`) |
| Owning service | `root_cause_service` |
| Read-only | Yes |
| Input parameters | `incident_id` (preferred) or `root_cause_id` |
| Required context | `incidentId` from launch context if present |
| Output DTO | `RootCauseResponse` (`cause`, `confidence_score`, `confidence_level`, `evidence: List[EvidenceResponse]`, `explanation`, `rule_version`, `status`, `created_at`, `updated_at`) |
| Evidence fields | `evidence[].type`, `evidence[].description`, `evidence[].weight`, `explanation` |
| Freshness metadata | `created_at`, `updated_at` (real fields) |
| Allowed filters | `incident_id` |
| Failure behavior | §22 |
| Forbidden endpoints | `PATCH /root-causes/{id}/confirm`, `PATCH /root-causes/{id}/reject`, `POST /root-causes/{id}/refresh` |

### 13.4 Business Impact Tool

| Field | Value |
|---|---|
| Purpose | Report the business impact assessment of an incident |
| Endpoints | `GET /api/v1/business-impact/{assessment_id}`, `GET /api/v1/business-impact?incident_id=` (both `BusinessImpactAssessmentResponse`) |
| Owning service | `business_impact_service` |
| Read-only | Yes — this service has no mutation endpoints at all |
| Input parameters | `incident_id` (preferred) or `assessment_id` |
| Required context | `incidentId` from launch context if present |
| Output DTO | `BusinessImpactAssessmentResponse` (`financial`, `customer`, `operational`, `sla`, `reputation`, `overall_score`, `overall_severity`, `business_priority`, `confidence`, `estimated_affected_customers`, `explanation`, `status`, `created_at`, `updated_at`) |
| Evidence fields | `explanation`, the five dimension levels, `confidence` (ARB-008: this is Business Impact's own stage-specific confidence, never conflated with Root Cause's) |
| Freshness metadata | `created_at`, `updated_at` (real fields) |
| Allowed filters | `incident_id` |
| Failure behavior | §22 |
| Forbidden endpoints | None exist on this service |

### 13.5 Investigation Tool

See §8 for the composition design. Field summary:

| Field | Value |
|---|---|
| Purpose | Assemble a cross-domain view of one incident (anomalies, root cause, business impact, latest recommendation, NLP context) |
| Endpoints | 5 calls across 5 services, listed in §8 |
| Owning service | None — Copilot-owned composition; each underlying fact remains owned by its source service |
| Read-only | Yes |
| Input parameters | `incident_id` (required) |
| Required context | `incidentId` — this tool cannot run without it |
| Output DTO | Copilot-internal composed evidence set (§16), not a new cross-service DTO — each sub-result keeps its own `sourceType`/`sourceId` |
| Evidence fields | Union of §13.3/§13.4/§13.1's evidence fields, plus NLP's enrichment summary fields |
| Freshness metadata | Per-source, from each underlying DTO (mixed: some sources have it, `nlp_service`'s enrichment summary should be checked at implementation time for a timestamp field) |
| Allowed filters | None beyond `incident_id` |
| Failure behavior | Partial-composition: if one of the 5 calls fails, return the others with an explicit gap statement (§22) — never block the whole answer on one failed source |
| Forbidden endpoints | Any mutation on any of the 5 services (§12) |

### 13.6 Analytics / Trend Tool

| Field | Value |
|---|---|
| Purpose | Answer volume/category/region/sentiment/urgency trend questions |
| Endpoints | `GET /api/v1/trends`, `/trends/daily`, `/trends/categories`, `/trends/regions`, `/trends/sentiment`, `/trends/urgency` (all on `anomaly_service`) |
| Owning service | `anomaly_service` (§9) |
| Read-only | Yes |
| Input parameters | `days` (period window; existing route parameter) |
| Required context | `timeRange`/`filters` from launch context, mapped to `days` where possible (§18) |
| Output DTO | `TrendSummaryResponse` / `VolumeTrendResponse` / `CategoryTrendResponse` / `RegionTrendResponse` / `SentimentTrendResponse` / `UrgencyTrendResponse` — all share a `period: str` field (e.g. `"last_30_days"`), no per-response computation timestamp |
| Evidence fields | The trend data points themselves (`date`, `count`, etc.) |
| Freshness metadata | **None available.** Verified: no `computed_at`/`generated_at`/`as_of` field exists anywhere in `anomaly_service/app/schemas/trends.py`. See §18 — Copilot must state the source provides no computation timestamp, never infer one. |
| Allowed filters | `days` (period window) only — region/category/sentiment breakdowns are dimensions of the *response*, not request filters, on today's endpoints |
| Failure behavior | §22 |
| Forbidden endpoints | None exist for trends |

### 13.7 Administration / Configuration Read Tool

| Field | Value |
|---|---|
| Purpose | Answer questions about platform/service health and Business Impact engine configuration |
| Endpoints | `GET /api/v1/administration/overview` (Gateway-only fan-out over every service's `/health`), `GET /api/v1/administration/intelligence-configuration` → `business_impact_service`'s `GET /api/v1/configuration/business-impact` |
| Owning service | Gateway (health fan-out composition) + `business_impact_service` (configuration) |
| Read-only | Yes |
| Input parameters | None |
| Required context | None |
| Output DTO | `AdministrationOverviewResponse`, `BusinessImpactConfigurationResponse` |
| Evidence fields | Per-service health status; configuration weights/thresholds |
| Freshness metadata | Health checks are inherently point-in-time (each call re-checks `/health` live) |
| Allowed filters | None |
| Failure behavior | §22 |
| Forbidden endpoints | None (read-only by construction) |
| **Note on Gateway call** | `administration_overview` is itself a Gateway-only fan-out (not a domain service), exactly like Investigation/Analytics. It has a smaller blast radius (2 sources) and is explicitly accepted as a second exception to "no Copilot → Gateway," following the same reasoning as §8: Copilot re-implements the same simple `/health`-per-service loop directly rather than calling the Gateway's own aggregator. |

---

## 14. Evidence Model

### 14.1 Schema

```json
{
  "evidenceId": "E1",
  "sourceType": "incident | root_cause | business_impact | recommendation | anomaly | trend | configuration",
  "sourceId": "the real UUID/identifier from the owning service",
  "authority": "the owning service's name (see §14.2)",
  "timestamp": "created_at/updated_at/decided_at when the DTO provides one; omitted, never fabricated, when it does not"
}
```

**Evidence vs. Narrative:** The LLM may synthesize narrative (prose explaining/summarizing evidence). The LLM may never invent an `evidenceId`, `sourceId`, or `timestamp` — every evidence object is constructed by the tool adapter from a real tool result, before the LLM ever sees it, and the LLM may only *reference* an `evidenceId` that already exists in that turn's tool results.

### 14.2 Authority

Authority is defined by which service owns the fact, matching this platform's existing service-ownership convention (DATA-002, `docs/DECISIONS.md`):

| Fact | Authoritative service |
|---|---|
| Incident/anomaly state | `anomaly_service` |
| Root cause | `root_cause_service` |
| Business impact | `business_impact_service` |
| Recommendation content/decision | `recommendation_service` |
| NLP enrichment | `nlp_service` |
| Trend/volume data | `anomaly_service` |
| Business Impact configuration | `business_impact_service` |

No domain fact has two authoritative sources in this platform today, so *authority conflict* (two services disagreeing about the same fact) is not currently possible by construction. The conflict-handling rule below covers the case that matters in practice: two pieces of retrieved evidence that a user could plausibly read as contradictory (e.g., an incident's `status` says `resolved` while a `RootCauseResponse.status` says `unconfirmed`) — different facts, not a true authority dispute.

### 14.3 Conflict Handling

```
Evidence A + Evidence B → apparent disagreement → Copilot explains, never resolves
```

Copilot may: present both pieces of evidence, report each one's timestamp, state which service is authoritative for each specific fact (§14.2 — not "which one is right," since they aren't answering the same question).
Copilot must never: invent a winner, overwrite any domain data, recompute domain intelligence, or silently prefer whichever result "sounds more confident."

---

## 15. Freshness Rule (F3 — Resolved)

**No domain DTO is modified to add a freshness field for Phase 12.** Instead, freshness reporting is conditional on what each real DTO already provides:

- **If the source DTO has a real timestamp** (`created_at`, `updated_at`, `last_seen_at`, `decided_at` — confirmed present on incident, anomaly, root cause, business impact, and recommendation-decision DTOs): Copilot may state it, e.g. *"This root cause assessment was last updated at 14:20."*
- **If the source DTO has no timestamp** (confirmed: all six trend/analytics response shapes in `anomaly_service/app/schemas/trends.py` carry only a `period` string, no computation timestamp): Copilot must say so explicitly, e.g. *"The trend data covers the requested period, but the source does not provide a computation timestamp."*
- **Never** use request time as a stand-in for data freshness, and never say *"data is current as of now"* unless the underlying source explicitly supports that claim (none currently do — every domain service is queried synchronously per-request, not streamed).

This rule is part of the evidence/no-fabrication rules (§21) and applies to every tool in §13.

---

## 16. Time and Filter Interpretation

Natural-language filters (`"today"`, `"last 7 days"`, `"West region"`, `"high severity"`) must be converted to structured tool parameters using each tool's actual, bounded parameter set (§13). If a request cannot be represented by any tool's real parameters:

- Copilot must not silently drop the filter.
- Copilot must either ask for clarification or explicitly state the filter is unsupported by the available tools, naming what it *could* answer instead.

Concretely: `days`-based windows map to the Analytics/Trend Tool's `days` parameter; `incident_id`/`recommendation_id` map directly; category/region/sentiment/urgency are *response dimensions* the tools already return, not independent request filters — a request like "West region trend" is answered by calling `/trends/regions` and filtering the returned rows for the requested region client-side within Copilot, not by a region query parameter that does not exist on the endpoint.

---

## 17. Conversation Persistence (F4 — Resolved)

| Property | Value |
|---|---|
| Owner | `copilot_service` |
| Storage | Shared PostgreSQL (same instance every service already uses — ARCH-002, `docs/DECISIONS.md`) |
| Ownership model | `copilot_service`-owned tables, following the same DATA-002 service-ownership convention as every other service's entities |
| Conceptual tables | `copilot_conversations` (`conversation_id`, `created_at`, `last_message_at`, optional launch `workspace`/`incidentId`/`recommendationId` context snapshot), `copilot_messages` (`message_id`, `conversation_id`, `role`, `content`, `evidence_references` (JSON), `created_at`) |
| Retention | **No automatic expiry in the prototype** — consistent with every other entity in this platform (no service anywhere implements TTL/archival today; conversations are not treated as more sensitive than existing persisted domain data by default). Production retention/privacy policy (encryption at rest beyond the shared database's own posture, user-initiated deletion, automatic expiry) is explicitly identified as **future production hardening**, not a Phase 12 deliverable. |
| Not organizational memory | Conversation history exists only for follow-up-question continuity within a session/thread. It is never read by another user's conversation, never aggregated into a knowledge base, and never referenced by any domain service. ARB-002/ARB-005's long-term "Organizational Knowledge" vision is explicitly not started by this table. |

No migration, schema, or table is created by this document — this is the conceptual model implementation will build from.

### 17.1 Conversation Data Privacy

Conversation content may reference operational/customer detail retrieved from tools. Logging (§24) must never include full conversation history, full prompts, or full tool payloads — only bounded operational metadata. The conversation *table* itself is the only place full content is retained, inside `copilot_service`'s own storage boundary, subject to the same database access controls every other service's data already has (i.e., none beyond network-level isolation — consistent with, not weaker than, the rest of the prototype).

---

## 18. Step 7.X-Deferred Capability Rule (F5 — Resolved)

> A capability previously deferred from *frontend surfacing* is not automatically forbidden from Copilot use, but each such capability must be explicitly approved, individually, in the tool contract (§13) before a tool may call it.

This prevents silent reintroduction of a deliberately-withheld capability while not treating "not on the frontend yet" as equivalent to "must never be read." The one instance found in this repository (`GET /recommendations/statistics`, Step 7.X G-03) is resolved in §13.1 — **approved**, with the specific reasoning documented there. No other Step 7.X-deferred backend capability was found to have a real, callable read endpoint (Root Cause mutation, Administration governance/audit, and Dashboard dimensional filtering are deferred because the underlying *data/capability* does not exist yet, not merely because the frontend doesn't show it — so there is nothing for a Copilot tool to call).

---

## 19. Tool Execution Model & Bounds

```
Frontend → Gateway → Copilot → explicit read-only tool adapter → authoritative service
```

- Copilot must not call the public Gateway as a generic proxy (§8/§9's two explicitly accepted, narrow exceptions — Investigation and Administration/Configuration composition — are the only Gateway-adjacent calls, and even those call the *domain services*, never the Gateway itself).
- **Maximum tool rounds: 3** (a ceiling, not a target — the agent stops once sufficient evidence exists).
- Bounded: total tool execution time, total evidence item count, individual result size, conversation context size (exact numeric limits are an implementation-time configuration decision, not frozen here — they must exist, per this invariant, before Batch 3 ships).
- No unbounded agent loop is permitted under any circumstance.

---

## 20. LangGraph Boundary

LangGraph (if used, per §22) orchestrates only: `Question → Tool decision → Tool call → Evidence → Optional next tool (≤ 3 rounds) → Answer`. It is not, and must not become, the platform's workflow engine — it never recreates the NLP/Anomaly/Incident/Root-Cause/Business-Impact/Recommendation workflows, all of which remain owned by their existing services and untouched by Phase 12.

---

## 21. No-Fabrication Rule (applies to every section above)

Prohibited unless backed by a real tool result: fabricated analytics, incidents, recommendations, decision state, metrics, evidence, timestamps (§15), confidence values, tool results, or organizational knowledge. If a requested answer cannot be supported by real platform data, the Copilot must say so rather than approximate.

---

## 22. Failure Strategy

- **Copilot itself is optional.** If the LLM or `copilot_service` is unavailable, every existing workspace continues working exactly as before — Copilot has no write path into any other part of the platform, so its failure cannot degrade anything else.
- **If one tool call fails** (a downstream service is unreachable/errors), Copilot reports partial evidence, e.g. *"I retrieved the incident details, but the analytics source was unavailable, so I cannot verify the trend."* Never a fabricated substitute value, never a silently omitted gap.

---

## 23. Frontend Response Contract

```
CopilotResponse {
  answer: string
  keyFindings: string[]
  evidenceReferences: EvidenceReference[]   // §14.1 shape
  relatedEntities: { type, id }[]
  visualizationHint?: "trend" | "distribution" | "comparison" | "table"
  limitations: string[]
  conversationId: string
  requestId: string                          // Phase 11's existing X-Request-ID
}
```

No arbitrary HTML, executable content, or frontend code generation is ever returned by the LLM. `visualizationHint` is a closed enum the frontend interprets — never LLM-generated chart configuration.

### 23.1 Visualization Contract

```
Structured evidence → approved visualizationHint (closed enum) → existing frontend renderer
```

The frontend owns rendering entirely; the LLM only selects from the four allowed hint values (or omits the field).

---

## 24. LLM Architecture

```
Copilot Orchestrator → LLM Provider Adapter → configured provider/model
```

- **Provider/model:** configuration-driven, selected during implementation based on the repository's actual available environment/credentials at that time. **Not decided by this document** — no provider name, model name, or credential is specified or invented here (verified: zero LLM dependencies, zero LLM env vars, no `copilot_service/app/core/config.py` exist in the repository today).
- The orchestrator must not be tightly coupled to one provider's API — the adapter boundary is the enforcement point for this.
- No credentials are committed at any point; secrets are environment-injected the same way `POSTGRES_PASSWORD`/every other credential in this repository already is.

### 24.1 Prompt Architecture

```
System policy → Copilot role → Tool rules → Evidence rules → Safety rules
   → Conversation context → User request → Tool results
```

Retrieved operational data (complaint text, incident descriptions, tool results generally) is **untrusted data** — it must never be interpreted as agent instructions. Prompt-injection resistance is a required part of the implementation design for the batch that builds prompt construction (Batch 3), not optional hardening.

### 24.2 Data Minimization

Only the minimum evidence required to answer the current question is sent to the LLM — never full datasets, database dumps, credentials, API keys, `Authorization` headers, or unnecessary complaint/customer history beyond what the relevant tool's evidence fields (§13) already scope.

---

## 25. Phase 8 Boundary

`evaluation_service` (Phase 8) remains fully independent. Phase 12 introduces no dependency in either direction: `evaluation_service` does not consume Copilot artifacts, and Copilot's own tool registry does not include an Evaluation tool (§10 — deliberately excluded from the final list, even though `evaluation_service` has real read endpoints, to keep this boundary unambiguous). The Phase 12 evaluation harness (§26) is a separate system entirely, for agent behavior, not domain evaluation.

---

## 26. Evaluation Harness (F6 — Resolved)

**Owner:** `copilot_service` — conceptually `backend/services/copilot_service/evaluation/` (not created by this document; a structural placeholder for implementation to build, matching this repository's per-service-owns-its-own-concern convention).

**Independence:** Must not become a dependency of `evaluation_service`; `evaluation_service` must not become a dependency of it (§25).

**Measures:** tool selection correctness, answer grounding (is the answer supported by retrieved evidence), citation correctness (do evidence references correspond to real evidence objects), hallucination (invented metrics/incidents/recommendations/decisions/evidence/timestamps), conflict-handling (was a genuine disagreement disclosed, not silently resolved), unsupported-request handling (did it refuse/clarify rather than guess), scope preservation (were requested filters/time ranges honored), safety (did it remain read-only), and completeness (was important retrieved evidence actually included in the answer).

---

## 27. Phase 11 Observability Integration

No new telemetry stack. `copilot_service` already carries the full Phase 11 wiring (verified in `backend/services/copilot_service/app/main.py`): `CorrelationIdMiddleware`, `instrument_app` (Prometheus `/metrics`, HTTP metrics), `mount_readiness`/`readiness_check` (`service_readiness` gauge), `mount_unhandled_exception_logging`, `init_tracing` (OTel → Tempo). Nothing further is required to participate in the existing Frontend → Gateway → Copilot → Tool → Domain-Service trace topology — every hop in that chain already propagates `X-Request-ID` and W3C trace-context via the shared `correlation.py`/`tracing.py` primitives every other service uses.

Additional Copilot-specific operational metadata (logged as `safe_extra` on the existing shared structured logger, never as a new logging system): `copilot_request_id`, `conversation_id`, `tool_name`, `tool_duration`, `tool_success`, LLM provider/model identifier, LLM latency, token usage (if the provider exposes it), final status.

**Must never be logged by default:** full prompts, full tool responses, full conversation content, complaint/customer text, credentials, `Authorization` headers — the same discipline Phase 11 §3.12 already established, applied to Copilot's own new log call sites.

---

## 28. Phase 13 Boundary

No authentication, authorization, RBAC, JWT, production identity, or access-control policy is implemented in Phase 12. No parallel Copilot-only authorization system is introduced.

> Phase 12 Copilot operates within the prototype's existing unauthenticated environment — identical in this respect to every other Gateway route today. Production access control must be enforced when Phase 13 authentication/RBAC is implemented; Phase 12 creates no new security boundary and closes no existing gap.

---

## 29. Whole-Project Compatibility

Checked directly against the repository, not assumed:

| Phase / Area | Compatibility |
|---|---|
| Phase 1–9 (domain pipeline) | Untouched. Copilot reads already-persisted output; no domain engine gains a new caller that could change its behavior. |
| Phase 10 (frontend workspaces, Gateway/BFF) | Untouched. Gateway's 7 existing public routes, 5 aggregators, error envelope, and CORS config are unmodified. FE-001's Action-Center-retirement precedent (workspace responsibilities must not overlap) is honored — Copilot is explicitly not a sixth workspace, it is a cross-cutting overlay. |
| Phase 11 (observability) | Reused as-is (§27); no second logging/metrics/tracing/dashboard system introduced. |
| Phase 8 (evaluation) | Independent, no coupling either direction (§25). |
| Step 7.X decisions | §18 — each deferred-from-frontend capability requires individual Copilot approval; only one instance exists and is resolved (§13.1). No deferred *architectural* decision (Root Cause mutation, Administration governance persistence, Dashboard dimensional filtering) is reintroduced, because none of those have a real endpoint for a tool to call in the first place. |
| ARB-001–008 (platform identity, lifecycle, confidence discipline) | ARB-008 (stage-specific confidence, never unified) is directly honored: §13.3/§13.4 keep Root Cause's `confidence_score`/`confidence_level` and Business Impact's `confidence` as distinct evidence fields, never merged into one Copilot-invented score. ARB-002/ARB-005 (long-term Organizational Knowledge vision) is explicitly not started (§17). |
| REC-003 (no decision attribution) | Preserved exactly — §11 confirms the Decision Status Tool cannot answer "who decided." |
| DATA-002 (service-local read models) | Honored — Copilot's tool adapters call each service's real API (never import another service's ORM models), same pattern every existing service already follows for cross-service reads. |
| Phase 13 (future) | No capability pulled forward (§28); no architectural debt created that Phase 13 would need to undo — the tool/read-only boundary is designed so that adding auth later is a Gateway/Copilot-API concern, not a rework of the tool registry. |

No contradiction with any existing ADR in `docs/DECISIONS.md` was found.

---

## 30. Phase 12 Boundary (restated)

Phase 12 is AI interpretation and orchestration over intelligence that already exists. It is not new anomaly/root-cause/business-impact/recommendation intelligence, not autonomous remediation, not organizational memory/continuous learning/outcome optimization, not authentication/RBAC, not production alerting or incident management.

---

## 31. Definition of Done

**Product**
- [ ] Copilot accessible from the application shell (mounted once in `AppShell.tsx`, not per-workspace)
- [ ] Compact-by-default, expandable chat experience implemented
- [ ] Contextual entry from all 5 workspaces functions and passes only real, existing context fields
- [ ] Every existing workspace remains fully usable with Copilot closed/unused

**AI**
- [ ] Tool selection matches the question's actual intent in representative test cases
- [ ] Tool iteration is bounded (≤ 3 rounds) and observably stops early when evidence is sufficient
- [ ] Answers are grounded — every factual claim traces to a real `evidenceId` from that turn's tool results
- [ ] No fabricated evidence, timestamp, or metric in any tested scenario
- [ ] Conflicting evidence is disclosed, never silently resolved (§14.3)
- [ ] Unsupported filter/request scenarios produce a clarification or explicit refusal, never a silent drop

**Backend**
- [ ] Gateway's existing 7 public routes/5 aggregators are byte-for-byte unchanged
- [ ] `copilot_service` implements exactly the 7 tools in §10, no more, no fewer, without modification to any other service
- [ ] Every tool is verified read-only (no `POST`/`PUT`/`PATCH`/`DELETE` capability reachable from the LLM)
- [ ] Conversation persistence implemented per §17's conceptual model, `copilot_service`-owned
- [ ] Service ownership unchanged everywhere (no domain service gains a new write caller)

**Frontend**
- [ ] `CopilotResponse` (§23) renders correctly, including partial/degraded responses
- [ ] Evidence references render and resolve against real returned evidence, never an orphaned reference
- [ ] `visualizationHint` renders only through existing frontend renderers, never LLM-generated markup
- [ ] Loading, tool-running, partial-failure, empty-conversation, error, and retry states are all implemented (§32 lists the exact set)

**Observability**
- [ ] A Copilot request is traceable end-to-end: Gateway → Copilot → Tool → Domain Service, one connected trace
- [ ] Copilot's structured logs carry `request_id`/`copilot_request_id`/`conversation_id` and no prohibited content (§27)
- [ ] Copilot's `/metrics`/`/health`/`/health/ready` behave identically to every other service's (already true today, verified)

**Evaluation**
- [ ] The agent-evaluation harness (§26) runs and reports on all 9 measured dimensions
- [ ] At least one deliberately-conflicting-evidence scenario and one deliberately-unsupported-request scenario are exercised and correctly handled

**Architecture**
- [ ] No Phase 13 capability introduced (§28)
- [ ] No Step 7.X-deferred capability reintroduced without the explicit §18 approval process
- [ ] No domain intelligence duplicated or recomputed inside Copilot
- [ ] No arbitrary HTTP/DB tool exists anywhere in the codebase
- [ ] No mutation capability reachable from any tool (§12)

---

## 32. Frontend Implementation Constraints (F7 — Resolved)

`AppShell.tsx` is the preferred, and only correct, mounting point — it is the platform's single persistent application frame (confirmed: renders once at router root; only `<Outlet />`'s content changes between workspaces). A per-workspace mount would violate "mounted once, application-wide" (§4).

**No new UI library is introduced.** `frontend/src/shared/components/layout/Panel.tsx` (a static content-container panel) is the closest existing primitive but is not an overlay; no `Modal`/`Drawer`/`Dialog` exists in this codebase today. Implementation must define a small, purpose-built Copilot panel component rather than adopting a general-purpose modal/drawer dependency, reusing existing design tokens/CSS conventions from `Panel.module.css` and the AppShell's own styling approach.

The implementation batch (Batch 5) must explicitly account for, at minimum:

- Keyboard focus management on open/close; accessible button semantics for the floating trigger; keyboard dismissal (e.g. `Escape`)
- Panel focus trapping while expanded (without blocking the rest of the page from being read/scrolled, since the panel must not cover the app by default — §4)
- `z-index`/stacking behavior relative to the existing persistent `Sidebar`/`TopBar`
- Responsive/mobile behavior (the existing `AppShell` already has a distinct mobile nav pattern via `useDisclosure` — the Copilot panel's mobile behavior should be defined consistently with that existing pattern, not invented independently)
- Loading state, tool-running state (distinct from generic loading — the user should be able to tell "a tool is executing" per §19's bounded iteration), partial-failure state (§22), empty-conversation state, error state, and retry behavior

---

## 33. Architecture Decisions

Recorded in `docs/DECISIONS.md`, following this repository's existing ADR convention (see §35):

- **COPILOT-001 — Copilot Tool Boundary, Read-Only Authority, and Investigation/Analytics Composition.** Corrects the service-topology error (F1) and the read-only/tool-naming contradiction (F2); establishes the read-only invariant (§12) and the Investigation/Analytics composition design (§8/§9) as durable, cross-batch conventions.
- **COPILOT-002 — Copilot Conversation Ownership and Retention.** Establishes `copilot_service` table ownership and the prototype "no automatic expiry" retention policy (§17) as a documented, deliberate choice — not an oversight.

No ADR is recorded for the freshness rule (§15) or the Step-7.X tool-approval rule (§18): both are implementation-detail-level scoping rules flowing directly from COPILOT-001's read/no-fabrication authority boundary, not independent architectural principles.

---

## 34. Implementation Batch Plan

Six batches, dependency-ordered. **No batch is implemented by this document** — this is the plan a future implementation session executes one batch at a time, each ending in manual review and a manual Git commit before the next begins.

### Batch 1 — Copilot Service Foundation + Contracts + Configuration
**Scope:** `copilot_service/app/core/config.py` (settings, no invented values); `copilot_service` Gateway router skeleton (`/api/v1/copilot/*`, request/response Pydantic models matching §23's `CopilotResponse` shape, no LLM/tool logic yet — returns a structured "not yet implemented" or echo response); wiring `copilot_service`'s existing Phase 11 observability (already present, verify it still passes after real routes are added).
**Dependencies:** None (first batch).
**Files/components likely affected:** `backend/services/copilot_service/app/core/`, `.../app/api/`, `.../app/schemas/`; `backend/services/gateway_service/app/api/` (new copilot router), `.../app/core/config.py` (Gateway already has `COPILOT_SERVICE_URL` — verify wiring only).
**Verification boundary:** Gateway can reach `copilot_service`; contract shapes match §23 exactly; existing Gateway routes unaffected; full existing test suite still green.
**Stop condition:** Any change required to an existing service's behavior, contract, or database ownership.

### Batch 2 — Read-Only Tool Adapters + Evidence Normalization
**Scope:** The 7 tool adapters (§13) as plain, testable functions/classes inside `copilot_service` (no LLM/LangGraph wiring yet — directly callable and unit-testable); evidence normalization into the §14.1 schema; the Investigation Tool's 5-service composition (§8).
**Dependencies:** Batch 1 (needs the service skeleton to live in).
**Files/components likely affected:** `backend/services/copilot_service/app/services/` (or equivalent tool-adapter module), new httpx client wiring to the 5 domain services (mirroring `gateway_service/app/core/downstream.py`'s existing pattern for consistency, not by importing Gateway code).
**Verification boundary:** Every tool callable independently returns real data from real running services; every forbidden endpoint (§12) is verifiably unreachable from this code; freshness rule (§15) produces the correct statement per DTO.
**Stop condition:** A tool's actual required endpoint doesn't exist or doesn't return the field this document assumes — re-verify against the repository before proceeding, do not invent the field.

### Batch 3 — LLM Orchestration + LangGraph + Bounded Tool Iteration
**Scope:** LLM provider adapter (§24, provider selected at this point, not before); LangGraph orchestration graph (§20); prompt architecture (§24.1) including prompt-injection resistance; the ≤3-round bounded iteration loop and other bounds (§19).
**Dependencies:** Batch 2 (needs real tools to orchestrate).
**Files/components likely affected:** `backend/services/copilot_service/app/services/orchestrator/` (or equivalent), `requirements.txt` (LLM/LangGraph dependencies added here, not earlier), `.env.example` (provider config, no real secret committed).
**Verification boundary:** A representative question produces a grounded, evidence-cited answer within the round/time/size bounds; a deliberately-malicious "ignore previous instructions" string inside simulated tool-result content does not alter Copilot's behavior.
**Stop condition:** The chosen LLM provider's tool-calling interface is incompatible with the read-only adapter boundary as designed — re-derive the adapter shape, do not weaken the read-only invariant to fit the provider.

### Batch 4 — Conversation Persistence + Contextual Behavior
**Scope:** `copilot_conversations`/`copilot_messages` tables and migration (§17); conversation continuity (follow-up questions); contextual launch-parameter handling (§4.1) read-only against workspace Contexts.
**Dependencies:** Batch 3 (conversation turns need an orchestrator to persist around).
**Files/components likely affected:** `backend/services/copilot_service/app/models/`, `.../app/repositories/`, a new Alembic migration head.
**Verification boundary:** A follow-up question ("Why?") correctly uses prior turn context; no workspace Context (`DashboardContext` etc.) is ever mutated by any Copilot code path; migration is additive/reversible, consistent with this repository's existing migration discipline (REC-002/REC-003 precedent).
**Stop condition:** None anticipated beyond standard migration review.

### Batch 5 — Frontend Copilot Experience
**Scope:** Floating button + expandable panel mounted in `AppShell.tsx` (§32); `CopilotResponse` rendering, evidence rendering, `visualizationHint` handling via existing renderers; all states listed in §32.
**Dependencies:** Batch 1 (needs a real API contract to render against); can proceed in parallel with Batches 2–4 once Batch 1's contract is stable, since it only needs the *shape*, not the real intelligence, to build against (using representative fixture responses).
**Files/components likely affected:** New `frontend/src/shared/components/copilot/` (or equivalent) module; `frontend/src/app/layouts/AppShell.tsx` (mount point only — no restructuring of Sidebar/TopBar/WorkspaceLayout).
**Verification boundary:** Every existing workspace/route/test remains green with the Copilot panel present but closed; the panel opens/closes/expands correctly across the 5 contextual entry points; accessibility constraints in §32 are met.
**Stop condition:** Any change required to an existing workspace Context's public interface.

### Batch 6 — Evaluation Harness + Integration Verification + Closure
**Scope:** The agent-evaluation harness (§26); end-to-end verification across all 5 contextual entry points; Definition of Done (§31) sign-off; closure documentation update (`docs/PROJECT_STATUS.md`, `docs/CHANGELOG.md`, `README.md`, following the same discipline Phase 11's closure used).
**Dependencies:** Batches 1–5 (needs the complete system to evaluate).
**Files/components likely affected:** `backend/services/copilot_service/evaluation/` (or equivalent), documentation files only.
**Verification boundary:** Full §31 Definition of Done evaluated criterion-by-criterion with evidence, matching the PASS/PARTIAL/DEFERRED/BLOCKED discipline Phase 11's closure established.
**Stop condition:** Any unresolved §31 criterion is reported explicitly, not silently marked done.

---

## 35. ADR Numbering Convention

This repository's `docs/DECISIONS.md` uses category-prefixed sequential IDs (`ARCH-*`, `DATA-*`, `ANOMALY-*`, `INCIDENT-*`, `RCA-*`, `BI-*`, `ARB-*`, `EVAL-*`, `REC-*`, `FE-*`, `OBS-*`). `COPILOT-*` follows this existing convention directly; no new numbering scheme is introduced.
