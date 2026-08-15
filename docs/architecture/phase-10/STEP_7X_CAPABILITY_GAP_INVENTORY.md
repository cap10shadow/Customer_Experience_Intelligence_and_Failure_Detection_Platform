# Phase 10 — Intermediate Step 7.X
# Complete Capability Gap Inventory

**Status:** Inventory only. Nothing in the repository was modified to produce this document. No implementation has begun.
**Date:** 2026-08-12
**Scope boundary:** Between Phase 10 Step 7 (closed, committed) and Phase 11. Phase 11–13 work and future production hardening are explicitly excluded from Step 7.X candidacy (classifications D and E below).

---

## 1. Executive Summary

Phase 10 Step 7 delivered a real, verified integration: a BFF-style Gateway (`/api/v1/*`), a centralized frontend HTTP client, and genuine backend-sourced data for Dashboard, Investigation, Recommendation (read-only), and Analytics Trend Analysis, plus a working `BusinessImpactCompleted` fan-out to `recommendation_service` and `evaluation_service`. This audit confirms that baseline is intact and correctly implemented — the Gateway's cross-cutting foundation (CORS, correlation IDs, standardized error envelope, downstream timeouts, single shared HTTP client) has **zero gaps**.

Beyond that baseline, this audit found **34 distinct findings** across five workspaces, the event/persistence layer, and cross-document consistency. The findings split into three groups:

1. **Genuinely low-risk, high-value Step 7.X candidates (Classification A)** — real backend data or real backend endpoints already exist and are simply unwired. The clearest examples: Dashboard's "Supporting Evidence" section fabricates five illustrative cards while `anomaly_service` already exposes the exact category/region/sentiment/urgency trend endpoints that would make them real (§7); Administration's "Platform Overview" could show genuine service health today since all nine backend services already expose working `/health` endpoints (§11); and a `warnings` field is faithfully populated by the Gateway on both Dashboard and Investigation responses but is never rendered anywhere in the UI (§7, §8).
2. **Items requiring an explicit architectural/product decision before implementation (Classification G)** — most notably Recommendation Decision/Lifecycle (no domain model exists anywhere for accept/reject/defer — this is not a wiring gap, it's a missing domain concept), Analytics' three narrative sections (Pattern Discovery, Organizational Insights, Strategic Opportunities) which render specific fabricated content indistinguishable in styling from real data rather than using the honest-placeholder pattern the codebase already established elsewhere, and the orphaned `root_cause_service` confirm/reject/refresh mutation endpoints (a write capability that doesn't fit Step 7's "read integration only" precedent without a scope decision).
3. **Correctly out-of-scope items (D/E/F)** — Recommendation Effectiveness, Administration's User & Access Management and Audit & Change History, all authentication/RBAC, event-broker/Outbox/durable-retry infrastructure, and the Copilot service scaffold. These are legitimately Phase 11–13 or production-hardening work and are *not* recommended for Step 7.X.

No fabricated backend contracts, no fake filtering, and no silent business-state invention were found. Where the frontend shows illustrative content, it is in almost every case either explicitly wrapped in `FutureCapabilityPlaceholder` (honest) or, in a smaller number of cases (Analytics' three narrative sections, Dashboard's Supporting Evidence, Analytics' Executive Overview), rendered with the same visual weight as real data without a placeholder wrapper — these are flagged explicitly in §17 and are the most product-relevant findings in this inventory.

---

## 2. Current Phase 10 Baseline (Confirmed Intact)

Verified via direct code inspection, no gaps found:

- Gateway CORS: `backend/services/gateway_service/app/main.py:41-47`, `app/core/config.py:37,53-54` — configurable `CORS_ALLOWED_ORIGINS` via `CORSMiddleware`.
- Correlation ID propagation: `app/core/correlation.py:1-34`, wired at `main.py:39`.
- Standardized error envelope (`code`/`message`/`requestId`/`details`): `app/core/errors.py:15-117`, handlers at `main.py:52-54`.
- Downstream timeout handling (bounded, classified into 502/503/504): `app/core/downstream.py:12-35`, `DOWNSTREAM_TIMEOUT_SECONDS=5.0` in `core/config.py:33`.
- Single shared `httpx.AsyncClient`: `app/dependencies/http_client.py`, `main.py:24-31`.
- Registered Gateway routers: `dashboard.py`, `investigations.py`, `recommendations.py`, `analytics.py` under `/api/v1`, plus `/health` (`main.py:8-64`). No `administration.py`, no `evaluations.py` — confirmed absent, matching documented scope.
- No authentication/authorization dependency on any Gateway route — all routes are open today (confirmed, see §12).
- Action Center (FE-001) fully retired — only documentation/comment references remain, no live route/component/nav entry.

This baseline is **not re-audited generically** per the task's instruction to treat Step 7 as complete; it is cited here only as the fixed point every finding below is measured against.

---

## 3. Method / Repository Areas Examined

- **Documentation:** PRD.md, ARCHITECTURE.md, ROADMAP.md, README.md, PRODUCT_EXPERIENCE_GUIDE.md, docs/DECISIONS.md, docs/PROJECT_STATUS.md, docs/CHANGELOG.md.
- **Phase 10 architecture batch documents** (identified by content, not filename, per instructions):
  | File | Batch |
  |---|---|
  | `docs/architecture/phase-10/history/batch-1-integration-foundation-architecture.md` | Batch 1 — Integration Foundation Architecture |
  | `docs/architecture/phase-10/history/batch-2-workspace-api-backend-integration.md` | Batch 2 — Workspace → API → Backend Integration Architecture |
  | `docs/architecture/phase-10/history/batch-3-cross-service-pipeline-communication.md` | Batch 3 — Cross-Service Pipeline & Communication Architecture |
  | `docs/architecture/phase-10/history/batch-4a-api-data-contract-architecture.md` | Batch 4A — API & Data Contract Architecture |
  | `docs/architecture/phase-10/history/batch-4b-event-failure-contracts.md` | Batch 4B — Event & Failure Contracts |
  | `docs/architecture/phase-10/history/batch-4c-integration-readiness-pass.md` | Batch 4C — Final Integration Readiness Matrix |

  (Renamed and moved to `history/` during the documentation-professionalization pass — these were originally saved with generic "Pasted markdown" filenames.)
- **Frontend:** `frontend/src/workspaces/{dashboard,investigations,recommendations,analytics,administration}/**` (components, context, hooks, api), `frontend/src/app/**` (routing, shell), `frontend/src/shared/**`.
- **Gateway:** `backend/services/gateway_service/app/**` (api, core, services, schemas, dependencies).
- **Backend services:** `anomaly_service`, `root_cause_service`, `business_impact_service`, `recommendation_service`, `evaluation_service`, `ingestion_service`, `nlp_service`, `copilot_service` — routes, domain, persistence models, event publishers/consumers.
- Six parallel research passes were used to cover this ground without redundant rescans: (1) Dashboard + Investigation, (2) Recommendation, (3) Analytics, (4) Administration + Auth/RBAC, (5) Events + Persistence + Orphans, (6) Cross-document consistency + Gateway foundation + shell-level UI. Each traced the full Frontend → API → Gateway → Backend → Persistence chain and cited exact file:line evidence, reused below without re-verification unless a cross-check was needed.

---

## 4. Frontend → Backend Matrix

| Frontend capability | Workspace | Expected data | Current API | Gateway route | Backend source | Persistence | Gap | Class | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Time range | Dashboard | Real trend window | `dashboardApi.ts` | `dashboard.py` | `anomaly_service /trends/daily` | anomaly trend store | None | **B** | `dashboard_aggregator.py:24,77,119-120` |
| Region/BU/product/user scope | Dashboard | Real dimensional filtering | context state only | `dashboard.py:48-63` rejects non-empty | none | none | No data model for these dimensions; Gateway correctly rejects rather than fake-filters | **A** (build capability) / **C** (current rejection behavior) | `DashboardContext.ts:10,27-41` |
| Supporting Evidence (5 cards) | Dashboard | Category/region/sentiment/urgency trend summaries | none — hardcoded `DEFAULT_EVIDENCE_ITEMS` | not modeled (`dashboard.py:26-29` docstring: "deliberately absent") | `anomaly_service /trends/{categories,regions,sentiment,urgency}` exist and unused | anomaly trend store | Real backend capability exists and is unused; frontend fabricates the section instead | **A** | `SupportingEvidence.tsx:8-14`; `anomaly_service/app/api/trends.py:37,46,55,64` |
| Recommended Focus (`focusAreas`) | Dashboard | Derived focus areas | `dashboardApi.ts` | `dashboard_aggregator.py:192` hardcodes `[]` | none | none | Structurally guaranteed empty, not merely data-dependent | **A** | `RecommendedFocus.tsx:9,14` |
| `warnings` (partial-failure signal) | Dashboard, Investigation | Degraded-source notice | populated by Gateway | `dashboard.py`/`investigations.py` DTOs | real | n/a | Gateway computes it; no component renders it | **A** | `viewModel.ts` (both workspaces); zero JSX consumption confirmed |
| Evidence source "NLP Intelligence" | Investigation | Enrichment-derived evidence | schema literal exists, never emitted | `investigation_aggregator.py:148-156` | `nlp_service` has no incident-scoped enrichment listing (only by complaint_id/enrichment_id) | nlp enrichment store, unreachable by incident | Missing backend capability; current omission is honest | **A** (new endpoint) / **C** (current behavior) | `nlp_service/app/api/enrichments.py:63,81,99` |
| Business Impact confidence level | Investigation | Stage-specific confidence band | always `undefined` | `investigation_aggregator.py:98-109` hardcodes `None` | `business_impact_service` has raw `confidence:int`, no band classifier | `confidence` column unused | ARB-008-compliant (no fabrication), but classifier genuinely missing | **A** (build classifier) / **C** (current suppression) | `business_impact_assessment.py:22`; contrast `root_cause_service/app/domain/confidence.py` |
| Root Cause confirm/reject/refresh | Investigation | Analyst mutation workflow | none | none | real: `PATCH /{id}/confirm`, `/reject`, `POST /{id}/refresh` | root_cause table has confirm/reject state | Real write capability entirely unsurfaced | **G** | `root_cause_service/app/api/root_causes.py:65-114` |
| Recommendation Decision | Recommendation | Human decision record | frontend-fabricated constant (`DECISION` object) | schema explicitly states fields "deliberately absent" | none — zero decision/status/approve/reject fields anywhere in `recommendation_service` | none | Not rendered as an honest placeholder (unlike Alternative Options) — looks live, isn't | **A** (UX honesty fix) gated by **G** (real persistence scope decision) | `RecommendationsWorkspace.tsx:19-22`; `gateway_service/app/schemas/recommendations.py:21-26` |
| Recommendation Lifecycle | Recommendation | Stage progression state | frontend types model a lifecycle that isn't backed | same as above | same as above | same as above | Same root cause as Decision | **A**/**G** | `RecommendationLifecycle.tsx:17-23`, `types.ts:39-55` |
| Alternative Options / Expected Outcome / Risk Assessment | Recommendation | n/a — documented placeholders | `FutureCapabilityPlaceholder` | n/a | REC-001: engine doesn't preserve non-selected candidates | n/a | None — correctly honest | **C** | `AlternativeOptions.tsx:9-33` etc. |
| Recommendation `generationId` | Recommendation | Traceability display | fetched, not rendered | present in DTO | real | real | Real data unused in UI, not a defect | **C** | `viewModel.ts:6-10,33-41` |
| Analytics Trend Analysis | Analytics | Real trend narrative | `analyticsApi.ts` | `analytics.py:18-42` | `anomaly_service /trends` | anomaly trend store | None | **B** | `analytics_aggregator.py:18-61` |
| Analytics Executive Overview | Analytics | Rollup of the fetched period | hardcoded `OBSERVATIONS` strings, unrelated to fetched data | n/a | none (no incident/recommendation counts in `AnalyticsResponse`) | n/a | Fabricated boilerplate, not wrapped in a placeholder, and not even a real rollup of already-fetched view-model data | **A**/**G** | `ExecutiveOverview.tsx:7-11` |
| Analytics Pattern Discovery | Analytics | n/a — documented future state | hardcoded specific narrative rendered with full-fidelity styling | none | none | none | Presents fabricated specifics indistinguishable from real Trend Analysis output; inconsistent with the "honest future-capability state" the docs claim | **G** | `PatternDiscovery.tsx:7-14`, `PatternCard.tsx:27-40` |
| Analytics Organizational Insights | Analytics | n/a — documented future state | hardcoded narrative, non-placeholder | none | none | none | Same pattern as Pattern Discovery | **G** | `OrganizationalInsights.tsx:5-11` |
| Analytics Strategic Opportunities | Analytics | n/a — documented future state | hardcoded narrative, non-placeholder | none | none | none | Same pattern | **G** | `StrategicOpportunities.tsx:7-18` |
| Analytics Recommendation Effectiveness | Analytics | n/a — documented future state | `FutureCapabilityPlaceholder` | n/a | no outcome-tracking capability exists; but `RecommendationStatisticsService` (real counts/averages) exists unsurfaced | recommendations table | Placeholder itself correct; adjacent real capability orphaned | **C** (placeholder) / **G** (orphaned stats service) | `RecommendationEffectiveness.tsx:21-36`; `recommendation_service/app/application/recommendation_statistics_service.py:10-77` |
| Analytics filters row ("Filters: None active") | Analytics | Active filter state | hardcoded text, no filter state exists in context | n/a | n/a | n/a | Honest static text, not fabricated filtering | **D** | `ScopeIndicator.tsx:24-26` |
| Administration — all 6 sections | Administration | Varies | hardcoded per-component data | none (no `administration.py`) | see §11 | see §11 | See Administration Gap Analysis (§11) | **A/C/D/G** (mixed, see §11) | `frontend/src/workspaces/administration/**` |
| TopBar user identity | App shell | Real session identity | hardcoded `userName="Operations User"` | n/a | none (no auth) | n/a | Unlabeled hardcoded value; defensible given no auth exists, but undocumented as illustrative | **C** | `TopBar.tsx:41` |

---

## 5. Backend → Frontend Matrix

| Backend capability | Service | Endpoint/event | Persistence | Current frontend consumer | Expected consumer | Status | Class | Evidence |
|---|---|---|---|---|---|---|---|---|
| `/trends/{categories,regions,sentiment,urgency}` | anomaly_service | REST | trend store | none | Dashboard Supporting Evidence | Real, unconsumed | **A** | `anomaly_service/app/api/trends.py:37-64` |
| `/health` (all 9 services) | every service + Gateway | REST | n/a | none | Administration Platform Overview | Real, unconsumed | **A** | `backend/services/*/app/main.py` |
| Root cause confirm/reject/refresh | root_cause_service | `PATCH/POST` | root_cause table | none | Investigation (analyst action) | Real, unconsumed, is a write capability | **G** | `root_causes.py:65-114` |
| NLP enrichment by incident | nlp_service | not implemented (only by complaint_id/enrichment_id) | enrichment store | none | Investigation Evidence | Missing capability | **A** (new endpoint) | `enrichments.py:63,81,99` |
| `recommendation_service` list/statistics/generation/incident-scoped reads | recommendation_service | `GET /recommendations`, `/recommendations/statistics`, `/recommendations/generations/{id}`, `/incidents/{id}/recommendations[/latest]` | recommendations, recommendation_generations tables | none (Gateway only exposes single-item `/recommendations/{id}`) | A future Recommendations list/history view | Real, unconsumed | **D** | `presentation/api/recommendations.py:36-119` |
| `RecommendationStatisticsService` (counts/averages) | recommendation_service | not REST-exposed | recommendations table | none | Analytics (non-outcome activity summary) | Real, orphaned | **G** | `recommendation_statistics_service.py:10-77` |
| `RecommendationsGenerated` event | recommendation_service | in-process event | n/a | none | future subscriber | Real, unconsumed by design | **D** | `in_process_recommendation_event_publisher.py` |
| `EvaluationCompleted` event | evaluation_service | in-process event | n/a | none | future subscriber | Real, unconsumed by design | **D** | `evaluation_service/.../in_process_event_publisher.py` |
| `evaluation_service` full REST API (5 endpoints) | evaluation_service | REST | evaluations table | none — no Gateway route, no frontend workspace | undetermined — no Evaluation workspace scoped anywhere | Real, fully orphaned | **D** (flag **G** only if an explicit decision is wanted on whether Evaluation ever gets a UI) | `presentation/api/evaluations.py:30-82`; no `gateway_service/app/api/evaluations.py` |
| `business_impact_service` weighting/scoring constants | business_impact_service | not exposed | hardcoded module constants, not DB-backed | none | Administration Intelligence Configuration | Real values, no config-management layer | **G** | `weighting.py:12-18`, `scoring.py` |
| `copilot_service` | copilot_service | `/health` only | none | none | Phase 12 | Correctly scaffolded, no gap | **D** | `copilot_service/app/main.py` |
| `ingestion_service`, `nlp_service` primary APIs | ingestion/nlp | REST (by id) | complaints, complaint_enrichments | none downstream via HTTP (anomaly_service reads via DB, not HTTP) | n/a — pre-existing Phase 3/4 architecture | Working as designed | **F** | confirmed no `httpx`/`requests` cross-service calls; no Gateway proxy routes |

---

## 6. Architecture → Code Matrix

| Architecture requirement | Source | Expected capability | Actual implementation | Missing pieces | Class | Action | Evidence |
|---|---|---|---|---|---|---|---|
| `/api/v1/administration/*` namespace | Batch 4A §14 | Administration Gateway routes | Not implemented | Full route/aggregator/schema layer, plus real backend sources | **A** (Platform Overview only) / **D/G** (rest) | See §11 | No `gateway_service/app/api/administration.py` |
| "Don't fake this integration" (Administration) | Batch 4C §7 | Honest scope | Frontend renders hardcoded illustrative data with explicit self-documentation (ADM-004 pacing rule) and a fake `setTimeout` loading transition | None — correctly honest | **B** | No action | `AdministrationWorkspace.tsx:42-50`, `IntelligenceConfiguration.tsx:8-30` |
| Workspace-oriented Gateway APIs, not one giant `/dashboard` endpoint | Batch 4A §2 | Per-workspace routes | Implemented exactly as specified | None | **B** | No action | `gateway_service/app/api/{dashboard,investigations,recommendations,analytics}.py` |
| `BusinessImpactCompleted` → parallel fan-out to Recommendation + Evaluation | Batch 4B §4B-1 | Independent consumers, idempotent | Implemented; identifier discipline (`event_id`≠`incident_id` etc.) verified correct in ORM models | None | **B** | No action | `recommendation_model.py:73-76`, `evaluation_model.py:60-65` |
| No broker/Outbox/durable retry at this stage | Batch 3 §15/§18, Batch 4B §4B-8/13 | In-process event delivery only | Implemented exactly as specified (EVAL-001) | None expected | **E** (correctly deferred, not a gap) | No action | `in_process_event_publisher.py` (both services) |
| Gateway error/timeout/CORS/correlation foundation | Batch 1 §7/12/15/17, Batch 4B §4B-9/10 | Full implementation | Implemented exactly as specified | None | **B** | No action | See §2 |
| "0% frontend-to-backend connectivity" / "Gateway exposes only /health" | Batch 4C §1 | (historical snapshot, pre-Step-7) | Superseded by Step 7 completion | N/A — obsolete audit finding, correctly tracked as historical | **F** | No action | `docs/PROJECT_STATUS.md:62,72,88` |
| Stage-specific confidence (ARB-008) | docs/DECISIONS.md | Never share one confidence scale | Root Cause and Business Impact confidence are kept separate; Business Impact confidence is currently suppressed entirely rather than shared, because no band classifier exists | Business Impact needs its own classifier | **A** (classifier) | Build in Step 7.X | `gateway_service/app/core/confidence.py:27-38` vs `business_impact_assessment.py:22` |
| Recommendation Decision/Lifecycle deferred to Step 7.X | docs/PROJECT_STATUS.md | Documented deferral | Frontend renders a non-placeholder fabricated Decision object instead of the honest-placeholder pattern used elsewhere in the same workspace | Inconsistent placeholder discipline | **A**/**G** | UX fix now; persistence scope is a decision | `RecommendationsWorkspace.tsx:19-22` |
| Analytics Pattern Discovery/Organizational Insights/Strategic Opportunities "remain honest future-capability states, not real data" | docs/PROJECT_STATUS.md:76 | Should read as clearly non-real | Rendered with identical chrome/confidence to real Trend Analysis cards, no placeholder wrapper | Placeholder-pattern inconsistency vs. Recommendation Effectiveness's correct implementation | **G** | Decide: wrap in `FutureCapabilityPlaceholder` or document the hardcoded-example pattern as intentional | `PatternCard.tsx:27-40`, `InsightCard.tsx:35-46`, `OpportunityCard` |

---

## 7. Dashboard Gap Analysis

| Filter/section | Frontend | API | Gateway | Backend | Genuinely applied? | Class |
|---|---|---|---|---|---|---|
| timeRange | ✓ | ✓ | ✓ | ✓ (`anomaly_service`) | Yes | **B** |
| region | plumbed, no UI control | — | rejects if non-empty | none | No — correctly rejected, not faked | **C** (rejection) / **A** (build capability) |
| businessUnit | plumbed, no UI control | — | rejects if non-empty | none | No — correctly rejected | **C**/**A** |
| productScope | plumbed, no setter exposed | — | rejects if non-empty | none | No — correctly rejected, plus asymmetric setter gap | **C**/**A** |
| userScope | plumbed, no setter exposed | — | rejects if non-empty | none | No — correctly rejected, plus asymmetric setter gap | **C**/**A** |
| Operational Brief | ✓ | ✓ | ✓ | ✓ | Yes (single health indicator: complaint-volume only) | **B** |
| Recommended Focus | renders `[]` always | — | hardcodes `[]` | none | No — structurally empty | **A** |
| Decision Summary | ✓ | ✓ | ✓ (capped top 5) | ✓ (`recommendation_service`) | Yes | **B** |
| Investigation Entry Points | ✓ | ✓ | ✓ (capped top 2) | ✓ (multi-service enrichment) | Yes | **B** |
| Supporting Evidence | fabricated | — | not modeled | unused real capability exists | No | **A** |

P1-1 and P1-3 (no fake filtering; honest empty states) are preserved: unsupported filters are rejected with a 400, never silently accepted or faked. The one exception worth flagging is Recommended Focus, which is not a "no data today" empty state but a structurally-guaranteed-empty field — worth distinguishing from a genuine empty state in any Step 7.X work.

---

## 8. Investigation Gap Analysis

All five narrative sections (Observation, Evidence, Root Cause Analysis, Business Impact, Recommended Next Step) trace to real backend data. Two genuine gaps:

1. **Evidence section's "NLP Intelligence" source is never emitted** because `nlp_service` has no incident-scoped enrichment query — only by `complaint_id`/`enrichment_id`. The Gateway correctly omits it rather than fabricating it (**C** for current behavior), but the missing capability itself is a real Step 7.X candidate (**A**) once nlp_service can answer "give me enrichments for this incident."
2. **Business Impact confidence is always suppressed** because `business_impact_service`'s `BusinessImpactAssessment` carries a raw `confidence:int` with no band classifier equivalent to `root_cause_service/app/domain/confidence.py`. ARB-008 is respected (no cross-stage scale sharing occurs), but the dimension is simply unavailable. Building a Business-Impact-local confidence classifier is a clean, ARB-008-compliant Step 7.X candidate (**A**).

A third finding sits outside the five narrative sections: **root_cause_service's confirm/reject/refresh mutation endpoints are fully implemented but entirely unsurfaced** (no Gateway route, no frontend UI). This is the first *write* capability found in this audit — Step 7 established a read-only integration precedent for Investigation, so exposing analyst mutation actions is classified **G** (requires an explicit decision on whether Investigation should gain write capability in Step 7.X, or whether this stays deferred alongside Recommendation Decision/Lifecycle).

`warnings` is populated correctly by the Gateway on both Dashboard and Investigation responses but rendered nowhere — a real, low-risk Step 7.X UI gap (**A**).

One item could not be fully evidenced: both `DashboardSectionErrorGate.tsx` and `InvestigationSectionErrorGate.tsx` carry a doc comment flagging an unresolved "retry caveat... a Step 7 hardening item, not fixed in [prior part]." No further detail exists in the repository to determine the exact defect. Classified **G** — needs the original audit note this comment refers to.

---

## 9. Recommendation Gap Analysis

| Capability | Real / Partial / Placeholder / Missing | Class |
|---|---|---|
| Recommendation Overview, Rationale | Real | **B** |
| Alternative Options | Honest placeholder (REC-001) | **C** |
| Expected Outcome, Risk Assessment | Honest placeholder | **C** |
| Decision | **Fabricated, not honest** — a hardcoded constant styled as live data, unlike the three sections above | **A** (fix) / **G** (real persistence scope) |
| Recommendation Lifecycle | Same issue as Decision | **A**/**G** |
| Effectiveness/Outcome tracking | Missing entirely, matches ARB-002 long-term vision | **D** |

The read/decision boundary established in Step 7 ("only real backend fields are surfaced — no fabricated confidence, alternatives, risk, expected outcome, or decision/lifecycle state," per docs/PROJECT_STATUS.md) is **violated specifically by the Decision and Recommendation Lifecycle sections**, which do not use the `FutureCapabilityPlaceholder` component the other three deferred sections correctly use. This is the single clearest documentation-vs-implementation inconsistency found in the Recommendation workspace. No backend domain model for decision/status/approve/reject/defer exists anywhere in `recommendation_service` (verified by full-service grep) — building real persistence is a genuine architectural decision (new field on `RecommendationEntity`? new bounded context? who is the decision owner/actor?), not a wiring task, hence **G**. The minimum Step 7.X-safe action is making Decision/Lifecycle visually honest (same placeholder pattern as Alternative Options) independent of that decision.

`recommendationId`/`incidentId`/`generationId` identifier discipline is fully correct (**B**) — no conflation anywhere in Gateway DTOs, frontend types, or backend schemas. Real backend list/statistics/generation/incident-scoped read endpoints exist but are not Gateway-routed or frontend-consumed; this is a future Recommendations list/history view, not a current-scope gap (**D**).

---

## 10. Analytics Gap Analysis

| Section | Real backend source? | Presented honestly? | Class |
|---|---|---|---|
| Executive Overview | No | **No** — hardcoded boilerplate unrelated to the fetched period, not wrapped in a placeholder | **A**/**G** |
| Trend Analysis | Yes (`anomaly_service` trends) | Yes | **B** |
| Pattern Discovery | No | **No** — specific fabricated narrative with full-fidelity styling | **G** |
| Recommendation Effectiveness | No | **Yes** — correctly uses `FutureCapabilityPlaceholder` | **C** |
| Organizational Insights | No | **No** — same issue as Pattern Discovery | **G** |
| Strategic Opportunities | No | **No** — same issue | **G** |

This is the most significant honesty-discipline finding in the inventory: three of six Analytics sections present fabricated, specific narrative content (a recurring "checkout complaints correlate with provider changes" story invented across all three) with the exact same visual weight, confidence, and card chrome as the genuinely real Trend Analysis section — while `docs/PROJECT_STATUS.md` explicitly states these sections "remain honest future-capability states, not real data." The code does not currently make that honesty visible to a user. Recommendation Effectiveness, in the same workspace, demonstrates the correct pattern already exists and is cheap to apply. No business-intelligence/narrative computation was found leaking into the Gateway (`analytics_aggregator.py` is a pure DTO mapper) — the fabrication is entirely frontend-side, which somewhat limits risk but does not remove the honesty gap.

`RecommendationStatisticsService` (category/priority counts, average score — real, cheap, already implemented) is orphaned and could back a genuine, non-outcome "Recommendation Activity" mini-section without touching the effectiveness/outcome boundary — flagged as **G** since whether that belongs in Analytics or Recommendation Effectiveness's honest-placeholder zone is a product call, not purely an engineering one.

The Scope Indicator's analysis-period control is real and genuinely drives the fetch; its "Filters: None active" text is honest (no filter state exists to be active), not fabricated (**D**, not a gap to fix now).

---

## 11. Administration Gap Analysis

| Section | Real data available today? | Class |
|---|---|---|
| Platform Overview | **Yes** — all 9 backend services + Gateway expose working `/health` endpoints, unused | **A** |
| User & Access Management | No — zero user/role/permission model anywhere in the repo | **G** |
| Data Sources & Integrations | No — no connector/integration config model | **D** |
| Intelligence Configuration | Partial — real hardcoded weighting/scoring constants exist in `business_impact_service` but are unexposed and unowned by any config layer; making them live/editable/persisted is a design decision | **G** |
| Platform Governance | N/A by design — intentionally narrative/organizational, not meant to be data-backed | **C** |
| Audit & Change History | No — no audit-log table/model anywhere; net-new persistence feature, not a wiring gap | **D** |

The only clean, low-risk Step 7.X candidate in Administration is **Platform Overview → real service health aggregation**: it requires a new thin Gateway aggregation route calling nine already-running `/health` endpoints, no new persistence, and has no dependency on the authentication decision below. Every other Administration section either requires net-new persistence models (Data Sources, Audit) or directly borders the Phase 13 JWT/RBAC decision (User & Access Management, Intelligence Configuration write-back) and should not be pulled forward. `AdministrationContext`'s presentation-only scope (§9, per its own doc comment) and the fake `setTimeout` loading simulation are both intentional and correctly implemented per the "structure only" discipline Phase 10 Step 6 established — no action needed (**B**/**C**).

---

## 12. Authentication / RBAC Gap Analysis

**Finding: zero authentication or authorization exists anywhere in the stack.** Confirmed by targeted search across `backend/` and `frontend/` for user/role/permission models, JWT/session/login/password/bcrypt/oauth utilities, and Gateway route dependencies — none found. All Gateway and backend routes are open today; CORS is configured with `allow_credentials=True` and wide-open origins-by-config (not a code bug — matches Batch 1's frozen CORS design, but has no authentication layered on top of it).

This is **explicitly Phase 13 scope** ("JWT authentication, RBAC concepts" is a named Phase 13 deliverable per ROADMAP.md) and is correctly classified **E** (future production hardening), not a Step 7.X gap. It is the direct blocker for real User & Access Management in Administration (§11) and for the open-CORS-plus-no-auth condition, which is pre-existing platform-wide, not new to this audit (**F**).

---

## 13. Event / Cross-Service Gap Analysis

| Event | Producer | Consumer(s) | Identifier discipline | Class |
|---|---|---|---|---|
| `BusinessImpactCompleted` | `business_impact_service` | `recommendation_service`, `evaluation_service` (independent, idempotent) | Correct — `event_id`≠`incident_id` verified in both consumers' ORM models | **B** |
| `RecommendationsGenerated` | `recommendation_service` | None anywhere in the repo | n/a | **D** — designed for a future subscriber (DTO explicitly directs consumers to the REST API for full detail), not an oversight |
| `EvaluationCompleted` | `evaluation_service` | None anywhere in the repo | n/a | **D** — PROJECT_STATUS.md explicitly states evaluation_service is "ready to observe... once a real message broker is introduced," confirming forward-looking design |

`evaluation_service` additionally has a full 5-endpoint REST API with no Gateway route and no frontend workspace — fully orphaned, but consistent with there never having been an "Evaluation" workspace scoped in the five-workspace architecture. Classified **D**; flagged **G** only if the team wants an explicit decision on whether Evaluation ever gets a UI surface at all, since nothing currently rules it in or out.

No broker, Outbox, or durable retry exists anywhere — correctly so, per EVAL-001 and this task's explicit exclusion of that infrastructure from Step 7.X candidacy (**E**).

---

## 14. Persistence / Database Gap Analysis

- **Written and fully read:** `incidents`, `active_anomalies`/`anomaly_history`, `root_causes`, `business_impact_assessments`, `recommendations`, `recommendation_generations` (idempotency use) — all **B**.
- **Written, partially read:** `recommendations` — single-item read is Gateway-routed; list/statistics/generation/incident-scoped reads exist at the service level but aren't Gateway-routed (**D**, future list/history UI).
- **Written, never read externally:** `evaluations` table — full REST API exists, zero consumers (**D**, see §13).
- **Real but unexposed (not a table, but a persistence-adjacent finding):** `business_impact_service`'s weighting/scoring constants are hardcoded Python module constants, not DB-backed configuration — Administration's Intelligence Configuration has nothing to genuinely read/write against without first deciding whether these become live config (**G**).
- **No persistence exists (net-new, not a gap in existing data):** users/roles/permissions, audit/change-history log, data-source/integration connector config — all **D/G**, not Step 7.X wiring tasks.
- **State that should arguably be persisted but currently lives only as UI state:** `AdministrationContext` (active section, expanded sections, selected config item) — this is intentional per its own doc comment and Phase 10 Step 6's "presentation state only" design; not a gap (**B**).
- **Cross-service data flow:** `complaints` (ingestion_service) and `complaint_enrichments` (nlp_service) are read by their owning services only; `anomaly_service` reads them via direct DB access (per DATA-002 service-local read models), not HTTP — this is the established, working Phase 3–5 architecture and is pre-existing/unrelated to Step 7.X (**F**).

---

## 15. Error / Loading / Empty / Retry Gap Analysis

All five workspaces use the same shared pattern (`ErrorBoundary` + `onRetry`/`resetKeys`, section-level error gates, skeleton-first loading) consistently and correctly for every real data-backed section (**B** throughout). Two findings:

1. `DashboardSectionErrorGate.tsx` and `InvestigationSectionErrorGate.tsx` both carry a doc comment flagging an unresolved retry caveat "carried forward as a Step 7 hardening item" — insufficient detail in-repo to determine the exact defect (**G**). The same caveat is referenced in the Recommendation and Analytics section error gates.
2. `warnings` (a genuine partial-failure/degraded-source signal, populated correctly by the Gateway on Dashboard and Investigation responses) is never rendered by any component on either workspace — a real gap in otherwise-correct error handling (**A**).

No unnecessary or invented UX patterns were found; all loading/error/empty states reuse the established shared components.

---

## 16. Orphan / Dead / Unused Capability Findings

| Item | Type | Class |
|---|---|---|
| `anomaly_service /trends/{categories,regions,sentiment,urgency}` | Backend endpoint, no consumer | **A** (should back Supporting Evidence) |
| All 9 services' `/health` endpoints | Backend endpoint, no aggregated consumer | **A** (should back Platform Overview) |
| `root_cause_service` confirm/reject/refresh | Backend endpoint, no consumer | **G** |
| `recommendation_service` list/statistics/generation/incident-scoped reads | Backend endpoint, no Gateway route | **D** |
| `RecommendationStatisticsService` | Backend capability, not REST-exposed | **G** |
| `evaluation_service` full REST API | Backend endpoint, no Gateway route, no frontend | **D** |
| `RecommendationsGenerated`, `EvaluationCompleted` events | Published, zero consumers | **D** (by design) |
| `warnings` DTO field (Dashboard, Investigation, Analytics) | Frontend-fetched, never rendered | **A** (Dashboard/Investigation) / **F** (Analytics — always `[]`, harmless dead field) |
| `EvidenceSource` Literal values `"NLP Intelligence"`, `"Root Cause Analysis"` | Schema literal, never emitted by aggregator | **C** (dead code shadow of §8 finding 1, not independently actionable) |
| `productScope`/`userScope` context setters | Missing, asymmetric with `region`/`businessUnit` (which have setters but also no callers) | **A** (normalize) |
| `copilot_service` | Fully scaffolded, `/health` only, no routes, no frontend reference | **D** — correctly labeled, Phase 12 |
| Action Center | Fully retired; only doc/comment references remain | **B** — no gap |
| Top-level frontend components | All reachable via router; no orphaned workspace components found | **B** — no gap |

---

## 17. Fabricated / Illustrative UI Findings

This is the audit's most product-sensitive section. Findings are grouped by how honestly they present their non-real status:

**Correctly honest (no action needed, Class C):**
- Recommendation: Alternative Options, Expected Outcome, Risk Assessment (`FutureCapabilityPlaceholder`, cites REC-001 explicitly).
- Analytics: Recommendation Effectiveness (`FutureCapabilityPlaceholder`).
- Administration: all six sections (explicit doc comments — ADM-004 pacing rule, "configures intelligence; never interprets it") plus the fake `setTimeout` loading simulation, which mimics an async transition but never claims to be real data.
- App shell: `NotificationButton`'s unread state defaults to `false` with an explicit doc comment disclosing it is "not wired to any real data source in this phase."

**Presented with more confidence than their status warrants (recommend a decision, Class A or G):**
- Dashboard Supporting Evidence — five illustrative cards with no placeholder wrapper, while real backend data exists to back them (**A** — straightforward fix, build the real version).
- Recommendation Decision and Recommendation Lifecycle — a fabricated constant and a modeled-but-unbacked lifecycle type, styled identically to real Recommendation sections, with a persistent status badge in the navigator (**A** for honesty fix, **G** for real persistence).
- Analytics Executive Overview — hardcoded boilerplate unrelated to the actually-fetched period (**A**/**G**).
- Analytics Pattern Discovery, Organizational Insights, Strategic Opportunities — specific fabricated narratives (the same invented "checkout/provider" story recurs across all three) rendered with full visual parity to genuinely real Trend Analysis content, undermining the "honest future-capability state" the documentation claims for them (**G** — needs a decision: wrap in `FutureCapabilityPlaceholder` for consistency with Recommendation Effectiveness, or explicitly document the hardcoded-example pattern as an intentional UX pre-visualization choice).

**Low-risk, defensible but unlabeled (Class C, optional polish):**
- `TopBar.tsx:41` hardcodes `userName="Operations User"` with no auth system to source it from and no comment marking it illustrative — defensible given §12's findings, but inconsistent with `NotificationButton`'s explicit self-disclosure pattern next to it in the same shell.

No instance was found of a frontend component fabricating a *business decision or lifecycle state* that the architecture explicitly forbids inventing (approval/rejection/defer/decision-owner/effectiveness) as if it were real and persisted — the closest case (Recommendation Decision) fabricates the *presentation* of such a state without actually claiming persistence anywhere in code, which is why it is classified as a UX-honesty gap rather than a "fabricated business state" violation per se.

---

## 18. Documentation-vs-Code Mismatches

| Mismatch | Documents | Status | Class |
|---|---|---|---|
| Batch 4C's "0% frontend-to-backend connectivity" / "Gateway exposes only /health" | Batch 4C §1 vs. current code | Obsolete, correctly superseded by Step 7 completion; not a live contradiction | **F** |
| Internal iteration across Batch 1/3/4A/4B/4C | e.g., Batch 4C §15 explicitly revises Batch 1 §14's "fail whole aggregate" rule | Intentional iterative freeze, not an unresolved contradiction | **F** |
| PRD.md / ARCHITECTURE.md vs. PROJECT_STATUS.md / README.md | Cross-checked directly | No contradiction found — PRD.md makes no forward-looking integration claims; README.md accurately states Administration "remains presentation-only" and Recommendation/Analytics integration is scoped to read/trends only, matching code | **B** |
| Analytics "honest future-capability states" claim (PROJECT_STATUS.md:76) vs. actual rendering | docs/PROJECT_STATUS.md vs. `PatternDiscovery.tsx` etc. | Genuine mismatch — see §10/§17 | **G** |
| Recommendation Decision/Lifecycle "explicitly deferred" (PROJECT_STATUS.md:84) vs. rendering as live data | docs/PROJECT_STATUS.md vs. `RecommendationsWorkspace.tsx:19-22` | Genuine mismatch — see §9/§17 | **A**/**G** |
| Administration Gateway namespace "NEW BACKEND CAPABILITY REQUIRED" (Batch 4A) vs. code | Batch 4A §14 vs. `gateway_service/app/api/` | Consistent — code correctly has no `administration.py`, matching the documented gap | **F** (no mismatch, gap correctly tracked) |

---

## 19. Complete Classified Finding Register

*(Consolidated from §4–§18; each finding appears once here with its final classification. "§" references point to the section with full evidence.)*

**Class A — Build in Step 7.X (13 findings):**
1. Dashboard Supporting Evidence → wire real `anomaly_service` category/region/sentiment/urgency trends (§4, §7, §16)
2. Administration Platform Overview → real `/health` aggregation (§4, §11, §16)
3. `warnings` field rendering on Dashboard and Investigation (§4, §8, §15, §16)
4. Recommended Focus (`focusAreas`) — resolve structural emptiness (§4, §7)
5. Business Impact confidence classifier in `business_impact_service` (§4, §8)
6. NLP-service incident-scoped enrichment endpoint (§4, §8) — enables honest "NLP Intelligence" evidence
7. Recommendation Decision UX-honesty fix (placeholder pattern) (§9, §17)
8. Recommendation Lifecycle UX-honesty fix (placeholder pattern) (§9, §17)
9. Analytics Executive Overview — real rollup or explicit placeholder (§10, §17)
10. Dashboard region/businessUnit/productScope/userScope — normalize setter asymmetry (§7, §16) — normalization only; full filtering capability is **G/D**
11–13. (Sub-items of #1 and #2 above are tracked as one build task each per endpoint group, not separately enumerated.)

**Class G — Requires architectural decision (9 findings):**
1. Recommendation Decision/Lifecycle real persistence scope (§9)
2. Analytics Pattern Discovery/Organizational Insights/Strategic Opportunities honesty treatment (§10, §17) — one decision, three sections
3. `RecommendationStatisticsService` surfacing (Analytics vs. Recommendation, or neither) (§10, §16)
4. Root Cause confirm/reject/refresh surfacing (write-capability scope decision) (§8, §16)
5. Administration User & Access Management (borders Phase 13) (§11)
6. Administration Intelligence Configuration (live config decision) (§11, §14)
7. Section-level retry caveat (insufficient repo evidence) (§8, §15)
8. Evaluation Service UI surface (optional decision — currently correctly D) (§13)
9. Full Dashboard filter dimensions (region/BU/product/user) — new data model decision (§7)

**Class B — Already implemented (largest group):** Gateway foundation (CORS, correlation ID, error envelope, timeouts, HTTP client), Dashboard timeRange/Operational Brief/Decision Summary/Investigation Entry Points, Investigation Observation/Root Cause/Business Impact narrative/Recommended Next Step/traceability, Recommendation Overview/Rationale/identifier hygiene, Analytics Trend Analysis, event identifier discipline, `AdministrationContext` scope, Action Center retirement, five-workspace nav shell, five-workspace routing. (Full list in §2, §4–§6.)

**Class C — Intentionally presentation-only / honest placeholder:** Recommendation Alternative Options/Expected Outcome/Risk Assessment, Analytics Recommendation Effectiveness, Administration all six sections + loading simulation, `NotificationButton` unread state, `TopBar` hardcoded identity (borderline — recommend explicit labeling), Dashboard filter rejection behavior, Analytics "Filters: None active" text, `generationId` unused-in-UI, `EvidenceSource` dead literals.

**Class D — Future phase (Phase 11–13):** Recommendation Effectiveness/Outcome tracking, `RecommendationsGenerated`/`EvaluationCompleted` consumers, `evaluation_service` UI surface, Recommendation list/history view, Administration Data Sources & Integrations, Administration Audit & Change History, `copilot_service`.

**Class E — Future production hardening:** Authentication/RBAC (all), broker/Outbox/durable retry, section error-gate retry caveat (once diagnosed, likely hardening not a functional bug).

**Class F — Pre-existing/unrelated:** Open CORS + no auth (pre-existing condition), ingestion_service/nlp_service direct-DB cross-service reads, Batch 4C's obsolete connectivity snapshot, `warnings` in Analytics (always `[]`, harmless).

---

## 20. Proposed Final Step 7.X Scope (for review, not yet approved)

**Recommended for Step 7.X (Class A, low-risk, evidence-backed, no architectural prerequisite):**
- Dashboard Supporting Evidence → real trend data
- Administration Platform Overview → real service health
- Render the `warnings` partial-failure signal on Dashboard and Investigation
- Resolve Recommended Focus's structural emptiness
- Build a Business-Impact-local confidence classifier (ARB-008-compliant)
- Add an nlp_service incident-scoped enrichment endpoint (enables honest Evidence sourcing)
- Recommendation Decision/Lifecycle: apply the existing honest-placeholder pattern (UX-only, no persistence decision required)
- Analytics Executive Overview: replace boilerplate with a real rollup of already-fetched data, or wrap in a placeholder
- Normalize Dashboard scope-filter setter asymmetry

**Recommended for an explicit architectural decision before scoping further work (Class G):** Recommendation Decision/Lifecycle real persistence; Analytics narrative-sections honesty treatment; `RecommendationStatisticsService` surfacing; Root Cause confirm/reject/refresh; Administration User & Access Management and Intelligence Configuration; the section error-gate retry caveat; whether Evaluation Service gets a UI; full Dashboard filter dimensions.

This section is a proposal for review — it does not constitute approval of scope, per the task's explicit instruction that Step 7.X scope is frozen only after this inventory is reviewed.

---

## 21. Explicitly Excluded Phase 11–13 Work

Not included in Step 7.X candidacy, per instruction and confirmed by this audit to have no current-scope backing capability that would justify pulling them forward: Recommendation Effectiveness/Outcome tracking (ARB-002 long-term vision), `RecommendationsGenerated`/`EvaluationCompleted` real-world consumption, Administration Data Sources & Integrations, Administration Audit & Change History, `copilot_service` (Phase 12), structured logging/metrics/tracing/health-monitoring-as-a-platform-capability (Phase 11 — note: the *existing* per-service `/health` endpoints used for §11's Platform Overview finding are Step 7-era artifacts already in the codebase, not new Phase 11 observability infrastructure; using them is not scope creep into Phase 11).

---

## 22. Future Production Hardening Exclusions

Authentication/RBAC (JWT, sessions, login, RBAC concepts — Phase 13 per ROADMAP.md); message broker introduction; Outbox pattern; durable/retry event infrastructure; event replay; mTLS/service mesh; broader production security hardening; service-level database separation. None of these were found to have any partial implementation that would change this classification — the repository has zero code in any of these categories today (confirmed via targeted search), consistent with EVAL-001 and the platform's documented prototype-stage posture.

---

## 23. Items Requiring Architectural Decisions

Consolidated list (full detail in §19's Class G register and the relevant domain sections):

1. **Recommendation Decision/Lifecycle persistence** — what does a "decision" become in `recommendation_service`'s domain model? New field vs. new bounded context; who is the decision owner/actor? (§9)
2. **Analytics narrative-sections honesty treatment** — wrap Pattern Discovery/Organizational Insights/Strategic Opportunities in `FutureCapabilityPlaceholder`, or formally document the current hardcoded-example approach as intentional? (§10, §17)
3. **`RecommendationStatisticsService` ownership** — does a non-outcome "Recommendation Activity" summary belong in Analytics or Recommendation Effectiveness's zone, and does surfacing it risk implying effectiveness data that doesn't exist? (§10, §16)
4. **Root Cause confirm/reject/refresh scope** — does Investigation gain its first write capability in Step 7.X, or does this wait alongside Recommendation Decision/Lifecycle? (§8, §16)
5. **Administration Intelligence Configuration** — do `business_impact_service`'s hardcoded weighting/scoring constants become live, editable, persisted configuration, and who owns that safety/versioning surface? (§11, §14)
6. **Administration User & Access Management** — how far can real user/role data go before it requires the Phase 13 authentication decision? (§11, §12)
7. **Section error-gate retry caveat** — needs the original audit note the doc comments reference to diagnose precisely. (§8, §15)
8. **Evaluation Service UI surface** — intentionally never scoped, or worth an explicit "no UI planned" decision to close the ambiguity? (§13)
9. **Dashboard region/businessUnit/productScope/userScope real filtering** — what data model would these dimensions require, and is that model owned by `anomaly_service` or a new capability? (§7)

---

## 24. Recommended Implementation Order

*(Sequencing suggestion only — subject to the review this inventory is awaiting.)*

1. **Zero-risk wiring of already-real data** (no decisions needed): Dashboard Supporting Evidence, Administration Platform Overview, `warnings` rendering, Recommended Focus resolution, Dashboard setter normalization.
2. **Small, self-contained new capabilities** (no decisions needed, but net-new code): Business Impact confidence classifier, nlp_service incident-scoped enrichment endpoint.
3. **UX-honesty fixes with no persistence dependency**: Recommendation Decision/Lifecycle placeholder treatment, Analytics Executive Overview real-rollup-or-placeholder.
4. **Architectural decisions (§23)** — resolve before scoping any further implementation work in Recommendation Decision/Lifecycle persistence, Analytics narrative sections, Root Cause mutation surfacing, or Administration Intelligence Configuration/User Management.
5. **Everything else** remains correctly deferred to Phase 11–13 per §21–22.

---

## 25. Final Step 7.X Readiness Assessment

Phase 10 Step 7's baseline is confirmed intact and correctly implemented with zero gaps in the Gateway's cross-cutting foundation. This inventory identifies a bounded, evidence-backed set of genuine gaps: a handful of low-risk "wire the already-real data" items with no architectural prerequisite, a small number of honesty/consistency fixes to placeholder presentation, and nine items that legitimately require a product/architecture decision before they can be scoped as implementation work. No Phase 11–13 capability was found partially or accidentally implemented, and no current-scope capability was found completely unaccounted for. The inventory is sufficient, once reviewed, to convert every Class A finding directly into an implementation plan without a further broad rediscovery pass; Class G findings will each need a short, scoped decision (not a new audit) before the same is true of them.

**This inventory is complete. No implementation, modification, commit, or push has occurred. Awaiting review and Step 7.X scope approval.**