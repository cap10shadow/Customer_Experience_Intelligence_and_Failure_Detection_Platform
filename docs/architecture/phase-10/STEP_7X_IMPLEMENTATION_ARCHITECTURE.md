# Phase 10 — Step 7.X — Implementation Architecture

**Status:** Planning document. No source code, tests, or project-level documentation have been modified. No Git operations performed.
**Date:** 2026-08-12
**Sources:** `STEP_7X_CAPABILITY_GAP_INVENTORY.md`, `STEP_7X_SCOPE_FREEZE.md` (both authoritative, not re-derived here), plus targeted, evidence-specific reads of `recommendation_model.py`, `recommendations.py`/`schemas.py`, `business_impact_assessment.py`, `scoring.py`, `weighting.py`, `root_cause_service/app/domain/confidence.py`, `nlp_service` enrichment API/model, `anomaly_service` `Incident`/`ActiveAnomaly` models, `dashboard_aggregator.py`, `gateway_service/app/schemas/{analytics,investigation}.py`, `ErrorBoundary.tsx`/`DashboardSectionErrorGate.tsx`/`DashboardWorkspace.tsx`, `administration/types.ts`/`IntelligenceConfiguration.tsx`/`PlatformOverview.tsx`, `DashboardContext.ts`, `gateway_service/app/core/config.py` — no broader repository scan performed.

---

## 1. Purpose and Scope

Step 7.X exists to complete genuine Phase 10 product capabilities that were left missing, unwired, incomplete, or in violation of the platform's no-fabrication UX principle when Step 7 closed — without pulling Phase 11 (Observability & Reliability), Phase 12 (AI Copilot), Phase 13 (Production Hardening), or any production-hardening infrastructure (broker, Outbox, durable retry, mTLS, real authentication) forward. Its scope is fixed by `STEP_7X_SCOPE_FREEZE.md` and elaborated here into field-level implementation design, batch sequencing, and a Definition of Done — the last planning artifact before implementation begins.

---

## 2. Frozen Architectural Constraints

Carried forward unchanged from Step 7 and the Scope Freeze — implementation must preserve every one of these; none is renegotiated by this document:

- Gateway/BFF boundary — the frontend never calls a backend service directly; every new capability adds or extends a Gateway route.
- Three-model-layer separation (domain / persistence / DTO) — no layer imports another service's model directly (see DATA-002 below).
- No-fake-contract rule — no DTO field is added unless a real backend source populates it; absent capability stays absent from the contract (as `AnalyticsResponse`'s docstring already states outright: *"Representing them here — even as an empty list — would misrepresent an unimplemented capability... the frozen 'no fake API fields' rule forbids that"*).
- Service ownership / DATA-002 — no service imports another service's ORM models; cross-service reads use service-local read models only.
- `incident_id` ≠ `event_id`.
- `recommendation_id` ≠ `incident_id`.
- ARB-008 — confidence remains stage-specific; no shared scale, no reused thresholds across services.
- Internal event isolation — `/internal/events/*` is never Gateway-routed.
- `BusinessImpactCompleted` parallel fan-out — untouched by this scope.
- Existing error envelope (`code`/`message`/`requestId`/`details`), correlation IDs, and downstream timeout conventions — every new Gateway route reuses these, none is redesigned.
- Existing loading/error/empty/retry patterns (`ErrorBoundary` + `onRetry`/`resetKeys`, section error gates, skeleton-first loading) — every new UI surface reuses these components as-is.
- Phase 11/12/13 boundaries, as enumerated in the Scope Freeze §3/§4.

No new architectural principle is introduced anywhere in this document.

---

## 3. Final Step 7.X Scope

**Build:** A-01 through A-09 (one caveat on A-06's exact shape, see §11).
**Approved decision-gated:** G-01 (minimal Recommendation decision persistence), G-02 (Analytics narrative-section honest placeholders), G-05 (read-only Intelligence Configuration), G-08 (no Evaluation UI — decision only, zero build work).
**Diagnostic, now resolved:** G-07 — see §17. Diagnosis found no genuine defect; reclassified from G to **B** (already correctly implemented). No fix batch needed.
**Deferred/excluded:** G-03, G-04, G-06, G-09, editable/persisted Intelligence Configuration, all Phase 11/12/13 and production-hardening items per the Scope Freeze's DEFER/EXCLUDE list — unchanged, not re-litigated here.

---

## 4. Implementation Batches

### Batch 1 — Foundation
A-03 (shared warnings component), A-09 (Dashboard filter-scope setter normalization), G-08 (adopt "no Evaluation UI planned" — zero-cost decision, documented at closure, no code).

### Batch 2 — Existing backend → frontend wiring
A-01 (Dashboard Supporting Evidence), A-02 (Administration Platform Overview).

### Batch 3 — Small backend capabilities
A-05 (Business Impact confidence classifier), A-06 (NLP evidence — see §11 for the revised, honest shape), A-04 (Dashboard Recommended Focus).

### Batch 4 — UX honesty / presentation completion
A-07 (Recommendation Decision & Lifecycle placeholder correction), A-08 (Analytics Executive Overview), G-02 (Analytics narrative-section placeholders).

### Batch 5 — Approved decision-dependent capabilities
G-01 (Recommendation decision persistence), G-05 (read-only Intelligence Configuration).

### Batch 6 — Diagnostic + verification + closure
G-07's diagnosis is already complete (§17, folded in here as a documentation note only — no code change). Full regression, typecheck, lint, production build, `docker compose config`, real-service E2E for every changed flow, documentation sync at closure only.

No batch is split further than this; each batch is one coherent, independently-shippable unit of work.

---

## 5. Field-Level Implementation Design

### A-01 — Dashboard Supporting Evidence

**Frontend**
- Existing: `frontend/src/workspaces/dashboard/components/SupportingEvidence/SupportingEvidence.tsx` (currently renders hardcoded `DEFAULT_EVIDENCE_ITEMS`).
- Change: accept real `items` data instead of falling back to the default constant; remove the constant once real data is wired (or keep as an empty-state fallback string, not fabricated content).
- API module: `frontend/src/workspaces/dashboard/api/dashboardApi.ts` — no new function needed; the existing `GET /api/v1/dashboard` call already returns the whole `DashboardResponse`.
- Hook/state: `useDashboardData.ts` — no new hook; extend the existing view-model mapping.
- View model: `dashboard/api/viewModel.ts` — add a mapped `supportingEvidence` field.
- UI behavior: skeleton while `isLoading`; on success, render real category/region/sentiment/urgency summaries; on partial failure (see Gateway below), degrade gracefully per existing `warnings` semantics — do not blank the section.

**Gateway**
- Endpoint: extends existing `GET /api/v1/dashboard` (no new route).
- Downstream calls added in `dashboard_aggregator.py`: `GET {ANOMALY_SERVICE_URL}/api/v1/trends/categories`, `/trends/regions`, `/trends/sentiment`, `/trends/urgency` (all four already exist and are called nowhere today, per `anomaly_service/app/api/trends.py:37,46,55,64`).
- Aggregation: issued concurrently alongside the existing `incidents_task`/`trend_task`/`recommendations_task` (`asyncio.create_task`, matching the existing pattern at `dashboard_aggregator.py:80-82`).
- DTO: extend `schemas/dashboard.py` with a `SupportingEvidenceDTO` (or similar) list, added to `DashboardResponse`.
- Error mapping: these four calls are non-essential enrichments (the aggregator's own documented rule: *"Trend, recommendation, root-cause, and business-impact data are non-essential enrichments: a failure... degrades that specific piece of the response and is recorded in `warnings`, never fabricated"*) — same treatment applies here, appended to the existing `warnings` list.
- Timeout/correlation: inherited automatically from the shared `httpx.AsyncClient` / `get_json` helper already used by every other call in this file — no new configuration.

**Backend:** none — all four `anomaly_service` endpoints already exist and are stable.

**Integration:** Dashboard → `dashboardApi.ts` (unchanged) → `GET /api/v1/dashboard` → `dashboard_aggregator.py` (four new concurrent calls) → `anomaly_service` (existing) → `DashboardResponse` (extended) → `viewModel.ts` (new field) → `SupportingEvidence.tsx` (real render).

**Dependencies:** none.

---

### A-02 — Administration Platform Overview

**Frontend**
- Existing: `frontend/src/workspaces/administration/components/PlatformOverview/PlatformOverview.tsx` currently hardcodes `FACTS` (including a fabricated `"Platform status: Operating normally"` and `"License / edition: Enterprise (illustrative)"`) and `CONNECTED_SERVICES`.
- New: first API module for this workspace — `frontend/src/workspaces/administration/api/administrationApi.ts`; first data hook — `hooks/useAdministrationData.ts` (mirrors `useDashboardData.ts`'s shape: `{ data, isLoading, error, refetch }`).
- Change: `PlatformOverview.tsx` replaces the fabricated `"Platform status"` fact with a real aggregated status derived from the fetched service-health data; `ConnectedServiceCard`s render from the real per-service health list rather than the two-item hardcoded array. `"Platform version"`, `"Environment"`, `"License/edition"`, and `"Last configuration update"` have no real backend source today and remain illustrative (explicitly labeled, not silently left as-is — see §12's honesty note) unless later folded into a real config source.
- View model: new `administration/api/viewModel.ts` mapping health-check results to `PlatformOverviewFact`/`ConnectedService` shapes already defined in `types.ts`.
- UI behavior: loading skeleton via existing `AdministrationLoadingState`; empty/degraded state if a subset of services fail to report health (existing `AdministrationEmptyState` pattern, or inline per-card degraded state — implementation detail, not a new UX pattern).

**Gateway**
- **New** route file: `backend/services/gateway_service/app/api/administration.py` — the first Gateway surface for this workspace, registered in `main.py` alongside the four existing routers.
- Endpoint: `GET /api/v1/administration/overview`.
- Downstream calls: fan out to all nine `/health` endpoints (`ingestion`, `nlp`, `anomaly`, `root_cause`, `business_impact`, `recommendation`, `copilot`, `evaluation` — all eight already enumerated in `gateway_service/app/core/config.py:41-49`'s `downstream_service_urls` property — plus the Gateway's own `/health`), issued concurrently via `asyncio.gather`, matching the existing aggregator concurrency pattern.
- Aggregation: new `administration_aggregator.py`, structurally identical to `dashboard_aggregator.py` — one dataclass query object (none needed here, no query params), one `build_administration_overview()` function.
- DTO: new `schemas/administration.py` — `ServiceHealthDTO { name, status, ... }` list plus a derived overall `PlatformOverviewDTO`.
- Error mapping: a single unreachable service is a non-essential-per-service degradation, not a whole-request failure — each service's health check failing degrades only that `ServiceHealthDTO` entry (e.g., `status: "unreachable"`), appended to `warnings`; the endpoint itself never fails outright unless the Gateway's own process is unhealthy.
- Timeout/correlation: reuses the shared `httpx.AsyncClient` and existing `DOWNSTREAM_TIMEOUT_SECONDS` — no new configuration value needed.

**Backend:** none — every service's `/health` endpoint already exists and is stable.

**Integration:** Administration → new `administrationApi.ts` → `GET /api/v1/administration/overview` (new route) → new `administration_aggregator.py` (nine concurrent health checks) → each service's existing `/health` → new `AdministrationOverviewResponse` → new `viewModel.ts` → `PlatformOverview.tsx` (real render).

**Dependencies:** none, but is the largest single unit in Batch 2 since it establishes Administration's first Gateway namespace, first API module, and first data hook — every later Administration capability (Batch 5's G-05) builds on this same namespace.

---

### A-03 — Partial-failure `warnings` rendering (Dashboard + Investigation)

**Frontend**
- New: one shared component, e.g. `frontend/src/shared/components/feedback/PartialFailureNotice.tsx` (naming at implementation time), rendering a list of warning strings non-intrusively (not styled as a blocking error — these are genuine partial successes, not failures).
- Existing wiring points: `DashboardWorkspace.tsx` and `InvestigationsWorkspace.tsx` — both already receive `data?.warnings` (or equivalent) from their respective view models (`dashboard/api/viewModel.ts:24`, `investigations/api/viewModel.ts:18` per the inventory) but never render it.
- No API/Gateway/backend change — the `warnings` field is already correctly populated end-to-end (`dashboard_aggregator.py:76,108`, `InvestigationResponse.warnings` per `gateway_service/app/schemas/investigation.py:66`).
- UI behavior: render only when `warnings.length > 0`; otherwise nothing changes from today's behavior.

**Gateway/Backend:** none.

**Integration:** existing fetch → existing `viewModel.warnings` (already populated, verified via `dashboard_aggregator.py` and `investigation_aggregator.py`) → new shared component render in both workspaces.

**Dependencies:** none. Sequenced first (Batch 1) purely because it is the smallest, most self-contained unit and establishes the shared component Batch 2+ do not need but could reuse if a similar need arises.

---

### A-04 — Dashboard Recommended Focus

**Frontend**
- Existing: `RecommendedFocus.tsx` currently always renders an empty state because `focusAreas` is always `[]`.
- Change: render real `focusAreas` entries once populated; no new component needed, only real data.
- View model: `dashboard/api/viewModel.ts` — no shape change, `focusAreas` already exists as a field, just currently always empty.

**Gateway**
- Change: `dashboard_aggregator.py:192` currently hardcodes `focusAreas=[]` inside `_build_operational_brief()`. Per Task 12's explicit instruction ("do not create a new intelligence engine merely to populate a UI section... no unsupported business conclusions"), the only honest design is a **derivation from data already fetched for other sections in the same request** — specifically, the `active_incidents` and `recommendations` lists already retrieved by `_fetch_active_incidents`/`_fetch_recent_recommendations` for Operational Brief and Decision Summary.
- Proposed derivation (composition, not new intelligence): a focus area entry per active incident whose severity is `"high"`/`"critical"` **and** which has at least one associated recommendation already in the fetched `recommendations` list — i.e., "these already-surfaced critical situations already have an action available; prioritize reviewing them." This reuses two data sets already in memory in the same function call, invents no new scoring, and states only what is already true elsewhere on the same Dashboard response (critical situations exist; recommendations exist for them).
- If, at implementation time, this derivation is judged too close to "supported focus," the fallback is an **honest empty state** with explanatory copy (e.g., "No incidents currently need urgent focus beyond what's shown above") rather than any fabricated prioritization — Task 12's explicit instruction.
- DTO: no schema change — `focusAreas` already exists in `OperationalBriefDTO`.

**Backend:** none — no new backend capability, pure Gateway-side composition of already-fetched data.

**Integration:** Dashboard → `dashboard_aggregator.py` (`_build_operational_brief`, new derivation step using already-in-scope `active_incidents`/`recommendations`) → `RecommendedFocus.tsx` (real render or honest empty state).

**Dependencies:** benefits from being sequenced in the same batch as A-01/A-02 (same aggregator file, same review pass) but has no hard dependency on either.

---

### A-05 — Business Impact confidence classifier

**Preserving ARB-008:** this creates a **Business-Impact-owned** classifier, structurally independent from `root_cause_service/app/domain/confidence.py`. No import, no shared module, no shared band values.

**Existing evidence (confirmed by direct read):**
- `business_impact_service/app/domain/business_impact_assessment.py:22` already carries `confidence: int` — a raw 0-100 score.
- `business_impact_service/app/services/scoring.py:74-83`'s `compute_confidence()` already computes this score deterministically: *"the proportion of the five impact dimensions that carried an actual signal (non-NONE) rather than a default... NOT a probability or ML estimate — purely a measure of how complete the available intelligence was."*
- `root_cause_service/app/domain/confidence.py:9-14` shows the **pattern** to mirror structurally (a `List[Tuple[int, str]]` of `(upper_bound_inclusive, band)` pairs plus a `classify_confidence()` function) — but its actual band values (`30/50/70/90` → Weak/Low/Medium/High/Very High) are Root-Cause-domain-specific and must **not** be reused, per `gateway_service/app/schemas/investigation.py:52-58`'s own docstring, which explicitly forbids exactly that.
- `gateway_service/app/core/confidence.py:27-38` currently maps only Root Cause's bands; `investigation_aggregator.py:98-109` currently hardcodes `businessImpactConfidenceLevel=None`.

**Backend**
- New: `backend/services/business_impact_service/app/domain/confidence.py` — same structural shape as Root Cause's (bands list + classifier function + a `ConfidenceScore`-equivalent frozen dataclass), independently-defined band boundaries.
- **Required implementation-time decision, not invented here:** the exact band boundaries (e.g., is 50 "Low" or "Medium" for Business Impact?) cannot be justified from existing repository evidence — `compute_confidence()`'s semantics (proportion of five dimensions carrying signal) differ enough from Root Cause's rule-certainty semantics that copying the numeric boundaries would be arbitrary. This must be a short, explicit design choice made during Batch 3 implementation (e.g., informed by the fact that confidence can only take one of six discrete values — 0/20/40/60/80/100%, since it's `informative/5` — making banding almost a formality; this observation itself should inform the actual threshold choice at implementation time, not this document).
- No change to `scoring.py`'s `compute_confidence()` itself — the classifier consumes its existing output, it does not alter it.

**Gateway**
- Extend `gateway_service/app/core/confidence.py` with a second, separate mapping function for Business Impact's own bands (parallel to, never merged with, the existing Root Cause mapping).
- `investigation_aggregator.py:98-109` stops hardcoding `None` and calls the new Business Impact classifier against the real `confidence` int already present in the fetched business-impact payload.
- DTO: no new field — `businessImpactConfidenceLevel` already exists in `InvestigationResponse` (`gateway_service/app/schemas/investigation.py:59`), currently always `None`.

**Frontend:** none — `BusinessImpact.tsx` already has a `confidenceLevel` prop wired per the inventory; it becomes populated automatically once the Gateway stops suppressing it.

**Integration:** `business_impact_service` (new classifier, new module) → Gateway `core/confidence.py` (new mapping) → `investigation_aggregator.py` (stop hardcoding `None`) → `InvestigationResponse.businessImpactConfidenceLevel` (already-wired field) → `BusinessImpact.tsx` (already-wired prop, now populated).

**Dependencies:** none.

---

### A-06 — NLP-service incident-scoped evidence (STOP finding — revised design required)

**STOP finding, per Task 11's explicit instruction not to fabricate a missing link:** direct inspection confirms **no incident→complaint linkage exists anywhere in the data model**:
- `anomaly_service/app/models/incident.py` — `Incident` links only to `active_anomalies` via the `incident_anomalies` join table (`IncidentAnomaly`); it holds no `complaint_id` field and no relationship to any complaint.
- `anomaly_service/app/models/anomaly.py` — `ActiveAnomaly` is keyed by `entity_type`/`entity_value` (a *dimension*, e.g. category="billing" or region="west"), not by individual complaint records. Anomalies are statistical spikes over an aggregate dimension, not references to specific complaints.
- `nlp_service/app/models/complaint_enrichment.py` — `ComplaintEnrichment` is keyed by `complaint_id` only; no `incident_id` field exists or could be added without inventing a link nlp_service has no way to know.

**Conclusion:** the capability as originally described in the inventory ("NLP-service incident-scoped enrichment endpoint," implying a per-complaint evidence list for one incident) **cannot be built without fabricating a relationship that doesn't exist**. Building it as originally scoped would violate the no-fake-contract rule as surely as leaving it fabricated on the frontend does.

**The one honest alternative, available today:** an incident's anomalies each carry a real `entity_type`/`entity_value` dimension and a real detection time window (`first_detected_at`/`last_seen_at` on `ActiveAnomaly`, joined via `incident_anomalies`). `nlp_service` already supports filtering enrichments by `issue_category`, `start_date`, `end_date` (`nlp_service/app/api/enrichments.py:103-124`, the existing `list_enrichments` endpoint). If (and only if) an anomaly's `entity_type` corresponds to `IssueCategory` (needs a one-line confirmation against `backend/shared/constants/enums/complaint.py` at implementation time — not confirmed in this pass), a genuinely honest capability is: **"enrichment aggregate statistics (sentiment/urgency distribution, keyword frequency) for the same category and time window as this incident's anomaly signal"** — a real, non-fabricated, dimension-scoped aggregate, not a per-complaint evidence list.

**Recommended action:** treat A-06 as **provisionally approved for Batch 3, with its exact shape re-confirmed at implementation start** (a five-minute check of `IssueCategory`'s values against `entity_type`/`entity_value`'s actual values in practice) rather than blocking the whole batch. If that confirmation fails (dimension vocabularies don't line up), A-06 downgrades to **G** (a genuine cross-service semantic mapping decision) and should be pulled from Batch 3 without blocking A-04/A-05 in the same batch.

**If confirmed buildable:**
- Backend: new endpoint in `nlp_service/app/api/enrichments.py`, e.g. `GET /enrichments/summary?issue_category=&start_date=&end_date=`, returning aggregate counts/sentiment distribution — reuses the existing `list_enrichments`/`count_enrichments` repository methods' filter parameters, adds only an aggregation step.
- Gateway: `investigation_aggregator.py:148-156` gains a new call, populating the currently-dead `"NLP Intelligence"` `EvidenceSource` literal (`gateway_service/app/schemas/investigation.py:7`) with a real, clearly-labeled aggregate evidence item (e.g., "68% of billing-category complaints in this window were negative-sentiment" — not a per-complaint list).
- Frontend: none — `Evidence.tsx`/`EvidenceGroup.tsx` already render whatever `EvidenceSource` values arrive.

**Dependencies:** requires the one-time vocabulary confirmation above before Batch 3 implementation starts; does not block A-04 or A-05 in the same batch.

---

### A-07 — Recommendation Decision & Lifecycle UX honesty correction

**Frontend**
- `frontend/src/workspaces/recommendations/RecommendationsWorkspace.tsx:19-22` — remove the fabricated `DECISION` constant.
- `Decision.tsx`, `DecisionSummary.tsx`, `RecommendationLifecycle.tsx`, `LifecycleSummary.tsx` — swap to `FutureCapabilityPlaceholder`, the exact same shared component already correctly used by `AlternativeOptions.tsx`/`ExpectedOutcome.tsx`/`RiskAssessment.tsx` in the same workspace.
- The persistent "Pending Review" status badge in `RecommendationNavigator.tsx` (per the inventory) is removed or replaced with neutral "not yet decided" framing consistent with the placeholder treatment.

**Gateway/Backend:** none for this batch — this is the UX-only correction, independent of G-01 (Batch 5). Per Task 15's explicit instruction: *"Until G-01's real persistence is implemented, show an honest FutureCapabilityPlaceholder. After G-01 exists, only render the real fields actually supported."* This batch delivers the "until" state; Batch 5, if G-01 ships, replaces it with the "after" state — same component swapped for real data, not a second redesign.

**Integration:** purely frontend; no Gateway/backend change in this batch.

**Dependencies:** none. Structurally precedes Batch 5's G-01 (which, if approved and built, replaces this placeholder with the real Decision UI — see G-01's design in §6).

---

### A-08 — Analytics Executive Overview

**Frontend**
- `frontend/src/workspaces/analytics/components/ExecutiveOverview/ExecutiveOverview.tsx:7-11` — remove the hardcoded `OBSERVATIONS` strings.
- Real-rollup option (preferred per Task 13's ordering: *"Prefer real presentation from already-fetched Analytics data"*): compute simple, factual statements directly from the already-fetched `AnalyticsViewModel` — e.g., trend point count and date range already present in `volumeTrend`, category count already present in `categoryTrend` (both already returned by the existing `GET /api/v1/analytics/trends`, per `gateway_service/app/schemas/analytics.py:55-56`). No new field, no new backend call — pure frontend view-model composition, matching the same "compose from already-fetched data" discipline as A-04.
- No causal/evaluative language — only factual statements ("N days of trend data available across M categories"), matching the existing Trend Analysis section's own explicit no-ranking/no-causal-language discipline (already verified correct in the inventory).
- If a meaningful real rollup cannot be produced honestly from these fields alone at implementation time, fall back to `FutureCapabilityPlaceholder` per Task 13's explicit fallback instruction — no fabricated incident/recommendation counts either way, since `AnalyticsResponse` has none.

**Gateway/Backend:** none — uses data already being fetched by `useAnalyticsData.ts` for Trend Analysis; no new endpoint, no new DTO field.

**Integration:** purely a frontend view-model computation change over already-fetched `AnalyticsResponse` data.

**Dependencies:** none.

---

### G-02 — Analytics narrative-section honest placeholders (approved)

**Frontend only**
- `PatternDiscovery.tsx`, `OrganizationalInsights.tsx`, `StrategicOpportunities.tsx` — replace their hardcoded specific narratives (the recurring fabricated "checkout/provider" story) with `FutureCapabilityPlaceholder`, matching `RecommendationEffectiveness.tsx`'s already-correct usage in the same workspace.
- `PatternCard.tsx`, `InsightCard.tsx`, `OpportunityCard` — no longer need to render full-fidelity narrative chrome for content that isn't real; simplified to whatever `FutureCapabilityPlaceholder` needs, consistent with the other workspace's placeholder cards.

**Gateway/Backend:** none — explicitly, per the approval: *"Do not build the underlying intelligence capabilities."*

**Integration:** purely frontend; zero backend/Gateway change.

**Dependencies:** none. Batched with A-07/A-08 (Batch 4) since all three are the same class of change (remove fabricated-looking content, apply the existing placeholder pattern).

---

## 6. G-01 — Decision Persistence (Detailed Design)

The only approved persistence addition in Step 7.X — designed carefully per Task 8's instruction.

**Exact entity extension** (`backend/services/recommendation_service/app/infrastructure/persistence/models/recommendation_model.py`):

```
decision: Mapped[Optional[RecommendationDecision]] = mapped_column(Enum(RecommendationDecision), nullable=True, default=None)
decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
```

- New domain enum `RecommendationDecision` (new file, `backend/services/recommendation_service/app/domain/recommendation_decision.py`, mirroring the existing `RecommendationCategory`/`RecommendationPriority` enum pattern): `PENDING` (or `None` — nullable is preferred so "no decision yet" is `NULL`, not a sentinel enum value, consistent with `RecommendationDetailResponse`'s existing convention of `Optional[...]` fields meaning "not yet available" elsewhere, e.g. `businessImpactConfidenceLevel`) / `APPROVED` / `REJECTED` / `DEFERRED`.

**Nullable/default semantics:** all three new columns default to `NULL`. A `NULL` `decision` means "no decision recorded yet" — matches the existing codebase convention (e.g. `resolved_at` on `Incident`, `RootCauseExplanationDTO`'s optional fields) rather than inventing a `PENDING` sentinel that would need to be distinguished from "not yet fetched."

**Migration strategy:** one additive Alembic migration, three nullable columns, no backfill needed (every existing row gets `NULL` for all three — correctly represents "no decision was ever recorded for pre-existing recommendations," which is true).

**PATCH semantics:** new endpoint `PATCH /recommendations/{recommendation_id}/decision` in `recommendation_service/app/presentation/api/recommendations.py`.
- Request DTO: `{ decision: "approved" | "rejected" | "deferred", note: Optional[str] }`.
- Response DTO: the updated `RecommendationDetailResponse`, extended with the three new fields.
- **Idempotent/repeated-decision behavior:** a decision can be changed (e.g., `approved` → `deferred`) by issuing the PATCH again — each call overwrites `decision`/`decision_note`/`decided_at` unconditionally. This is a deliberate simplification: since there is no decision-owner/actor field (see below), there is no basis to distinguish "the same person changed their mind" from "someone else overwrote it" — building any conflict/versioning behavior would require the very attribution this design explicitly excludes. Silently overwriting is the honest choice given that constraint, not a shortcut.
- **Validation:** `decision` must be one of the three enum values (Pydantic enum validation); `note` is optional, unbounded-reasonable length (matches `explanation`/`rationale` fields' existing `Text` column convention, no artificial length cap invented).
- **Error behavior:** 404 if `recommendation_id` doesn't exist (matches the existing `get_recommendation` endpoint's behavior exactly, `recommendations.py:92-94`); 422 for an invalid enum value (FastAPI/Pydantic default, matches existing convention).

**Gateway mapping:** new `PATCH /api/v1/recommendations/{recommendation_id}/decision` route in `gateway_service/app/api/recommendations.py`, proxying to the backend PATCH, reusing the existing error-envelope/correlation-ID/timeout conventions (no new Gateway infrastructure). `recommendation_aggregator.py` (or a small dedicated function) maps the backend response into the existing Gateway DTO shape, extended with `decision`/`decisionNote`/`decidedAt`.

**Frontend state behavior:** `Decision.tsx`/`RecommendationLifecycle.tsx` (previously placeholder-only per A-07) gain a real form/action wired to the new Gateway route; on success, refetch or optimistically update the local view model; `RecommendationLifecycle.tsx`'s existing "Decision Before Lifecycle" structural rule (Phase 10 Step 4 — lifecycle stages never show until a decision exists) now has real data to gate on instead of always being unreachable.

**Preservation of `recommendation_id` and `incident_id`:** untouched — the new columns live on the same `RecommendationModel` row, keyed by the same existing `recommendation_id` primary key; `incident_id` remains a plain string column exactly as today (`recommendation_model.py:75`), no relationship or foreign key introduced.

**Explicitly NOT represented, per the approved scope:**
- Actor / decision-owner (who made the decision) — requires real identity, which doesn't exist until Phase 13 authentication.
- Approval authority / role-based sign-off — requires the same identity system.
- Authentication/RBAC of any kind on this endpoint — the PATCH is as unauthenticated as every other Gateway route today (consistent with the rest of the platform's current, documented state, not a new gap introduced by this feature).
- Broader approval workflow (multi-step approval, notifications, escalation) — out of scope; this is a single mutable decision record, not a workflow engine.

---

## 7. G-05 — Read-Only Configuration (Detailed Design)

**Trace: existing Business Impact constants → backend read endpoint → Gateway → Administration API → view model → Platform UI**

**Existing constants (confirmed by direct read, unchanged by this design):**
- `business_impact_service/app/services/weighting.py:12-18` — `DIMENSION_WEIGHTS` (Financial 0.35, Customer 0.25, Operational 0.15, SLA 0.15, Reputation 0.10).
- `business_impact_service/app/services/scoring.py:15-21` — `IMPACT_LEVEL_POINTS`; `scoring.py:36-41` — `SEVERITY_BANDS`.

**Backend:** one new read-only endpoint, e.g. `GET /configuration/business-impact` in `business_impact_service/app/api/business_impact.py` (or a new small `configuration.py` route module), returning the existing `DIMENSION_WEIGHTS`/`IMPACT_LEVEL_POINTS`/`SEVERITY_BANDS` dictionaries serialized as-is. **No import of these constants changes their module-level definition** — the endpoint reads the same Python objects the engine itself uses, guaranteeing the displayed value can never drift from the real, active engine behavior.

**Gateway:** new `GET /api/v1/administration/intelligence-configuration` in `administration.py` (same new route file as A-02), calling the new `business_impact_service` endpoint and mapping its response into a `ConfigurationItemDTO` list shape compatible with the frontend's existing `ConfigurationItem` type (`administration/types.ts:47-53`: `id`, `name`, `whatItIs`, `governs`, `currentValue`) — the Gateway supplies the human-readable `name`/`whatItIs`/`governs` narration (static, matching the existing three hardcoded `CONFIGURATION_ITEMS` entries' descriptive style) while `currentValue` is populated from the real fetched constant.

**Frontend:** `IntelligenceConfiguration.tsx` replaces its hardcoded `CONFIGURATION_ITEMS` array with fetched data via a new administration hook (reusing the API module/hook established in A-02's Batch 2 work); `ConfigurationItemCard.tsx` requires no change — it already renders whatever `ConfigurationItem` shape it's given.

**Explicitly ensured, per the approval:**
- Scoring/weighting *behavior* does not change — the endpoint is read-only and reads the same live constants the engine already uses; nothing in `business_impact_service`'s engine, rules, or scoring logic is modified.
- No database persistence — the values remain Python module constants; no new table, no migration.
- No mutation endpoint — only `GET`, no `PATCH`/`PUT`/`POST` for configuration anywhere in this design.
- No editable configuration model — the frontend's existing "editing affordance" visual pattern (per Administration's frozen UX spec) stays present but remains non-functional, exactly as it is today; this design does not wire it to anything.
- No governance workflow — out of scope entirely.

---

## 8. Test Architecture (per batch)

**Batch 1 (A-03, A-09, G-08):** frontend component tests for the new shared warnings component (renders when present, renders nothing when empty); frontend tests confirming `setProductScope`/`setUserScope` exist and update context state; no backend tests needed (no backend change).

**Batch 2 (A-01, A-02):**
- Backend: none new (no backend code changes) — existing `anomaly_service`/`*/health` test suites remain the coverage.
- Gateway: unit tests for `dashboard_aggregator.py`'s four new calls (success, partial failure → `warnings`, all four failing); new `test_administration.py` covering the new aggregator's health fan-out (all healthy, one unreachable → degraded entry + warning, timeout handling).
- Gateway API contract tests: new `GET /api/v1/administration/overview` — response shape, error envelope on total failure.
- Frontend: component tests for `SupportingEvidence.tsx` (loading/success/empty/partial-warning states) and `PlatformOverview.tsx` (same states).
- **Real-service E2E required** (per Scope Freeze §8): both A-02 (new Gateway route, new cross-service fan-out) and A-01 (new cross-service calls) must be verified against real running services and real HTTP, not mocks — matching Step 7's own established discipline.

**Batch 3 (A-05, A-06, A-04):**
- Backend unit tests: new `business_impact_service/app/domain/confidence.py` classifier (boundary values, clamping, determinism — mirroring `root_cause_service`'s existing confidence test pattern); new `nlp_service` aggregate endpoint (if A-06 proceeds) — filter correctness, empty-window behavior.
- Gateway tests: `investigation_aggregator.py`'s new confidence mapping (ARB-008 regression test: assert Business Impact bands are never equal to or derived from Root Cause bands — an explicit anti-regression test, not just a happy-path test); new NLP evidence call (if A-06 proceeds).
- Persistence: none for A-05/A-06 (no schema change); A-04 has no persistence either (pure composition).
- **Real-service E2E required** for A-05 and A-06 (new backend capability, cross-service integration) per Scope Freeze §8.
- No-fabrication test: assert `focusAreas` (A-04) never contains an entry not traceable to an already-fetched incident/recommendation ID in the same response.

**Batch 4 (A-07, A-08, G-02):**
- Frontend component tests only (no backend/Gateway change in this batch): `Decision.tsx`/`RecommendationLifecycle.tsx` render `FutureCapabilityPlaceholder` (not the old fabricated constant); `ExecutiveOverview.tsx` renders real computed text matching the fetched view model (or the placeholder fallback); `PatternDiscovery.tsx`/`OrganizationalInsights.tsx`/`StrategicOpportunities.tsx` render `FutureCapabilityPlaceholder`.
- Regression tests: confirm no existing Analytics/Recommendation test hardcoded an assertion against the now-removed fabricated content (the inventory did not find any such coupling, but this must be verified during implementation, not assumed).

**Batch 5 (G-01, G-05):**
- Backend: `RecommendationDecision` enum tests; PATCH endpoint tests (success, repeated-decision overwrite behavior, 404, 422); **persistence/migration tests are required** — migration applies cleanly to a populated table, existing rows get `NULL` for all three new columns, rollback works.
- Gateway: new PATCH route tests (success, error propagation, correlation ID preserved); new read-only configuration route tests.
- Frontend: `Decision.tsx` real-data rendering and submission flow tests; `IntelligenceConfiguration.tsx` real-data rendering tests.
- Identifier-integrity test (explicit, matching the platform's existing discipline): assert a decision PATCH never alters `recommendation_id` or `incident_id`.
- **Real-service E2E required** for both (new persistence, new Gateway routes) per Scope Freeze §8 — including a live migration-applied-then-verified check, not merely a unit test against an in-memory model.

**Batch 6:** no new capability, so no new unit tests — this batch is the full regression + verification pass (§9).

---

## 9. Verification Strategy

Final Step 7.X verification (Batch 6) must include, exactly as the Scope Freeze specifies:

- Full backend test suite (all services, including the new/extended `business_impact_service`, `recommendation_service`, `nlp_service` if A-06 proceeds, and `gateway_service` tests from every batch above).
- Full frontend test suite (all workspace test files, including new Dashboard/Administration/Recommendation/Analytics coverage from every batch).
- Backend typecheck (mypy) and frontend typecheck.
- Backend and frontend lint.
- Frontend production build.
- `docker compose config` validation (no new services are introduced by this scope, so this should remain a low-risk check, but it must still be re-run since `gateway_service/app/core/config.py` gains no new settings in this scope — confirmed, since `downstream_service_urls` already lists every backend service Step 7.X's new Gateway calls need).
- Real-service HTTP verification for every batch flagged above (A-01, A-02, A-05, A-06, G-01, G-05) — against real running services and real PostgreSQL, not mocks, matching Step 7's own established discipline (explicitly required by Scope Freeze §8, not optional).
- Database migration verification (G-01 only) — applied against a populated table, not just an empty test database.
- Identifier integrity — `recommendation_id`/`incident_id`/`event_id`/`generation_id` distinctness re-verified wherever G-01 touches `RecommendationModel`.
- Gateway boundary — confirm no new frontend code calls a backend service URL directly; every new capability routes through `/api/v1/*`.
- No-fabrication audit of every changed area — a targeted, scoped review (not a repository-wide re-audit) confirming no new DTO field lacks a real source and no placeholder was replaced with a different fabrication.
- Regression verification of all Step 7 capabilities (Dashboard, Investigation, Recommendation read, Analytics Trend Analysis, `BusinessImpactCompleted` fan-out) — full suite green, no capability degraded.
- No browser-based E2E is claimed or required: this repository has no browser automation framework (Playwright/Cypress/etc.) in its current test tooling per the existing Step 7 verification precedent (backend/frontend automated suites + manual real-service HTTP verification only) — consistent with Task 18's explicit instruction not to claim browser E2E where none exists.

---

## 10. Documentation Strategy

No project-level documentation is updated per batch. At final Step 7.X closure only, update:

- `docs/PROJECT_STATUS.md` — Step 7.X completion summary, following the exact section style already used for Step 7's own closure entry.
- `docs/CHANGELOG.md` — entries for each shipped capability, matching existing entry style.
- `docs/DECISIONS.md` — new ADR entries for the accepted G-01/G-05 minimal designs (e.g. `REC-003` for decision persistence scope, an `ADM-00X` entry for read-only configuration exposure — exact IDs assigned at closure time following the document's existing numbering convention) and a short entry recording the G-08 decision ("no Evaluation UI planned") and the G-07 outcome ("retry mechanism already correctly implemented; no defect found").
- `ROADMAP.md` — only if Phase 10's status wording needs adjustment; likely unnecessary since Phase 10 is already marked complete and Step 7.X is intentionally a sub-step, not a roadmap phase.
- `README.md` — only if implementation materially changes the current implementation-status description (e.g., Administration moving from "presentation-only" to "partial real integration" would need a wording update; Recommendation Decision moving from "no lifecycle" to "minimal decision capture" likewise).

No new documentation file is created merely for documentation's sake — these are the only five candidate files, and only the ones materially affected are touched at closure.

---

## 11. Definition of Done

Step 7.X is complete only when:

- Every approved capability (A-01…A-09, G-01, G-02, G-05, G-08) is implemented or intentionally resolved as a placeholder, **or**, for A-06 specifically, resolved either as the honest dimension-scoped aggregate design (§5) or explicitly reclassified to G and deferred if the category-vocabulary confirmation fails — not silently dropped either way.
- G-07 is documented as diagnosed and resolved (no fix required — see §17) rather than left as an open item.
- Frontend/backend/Gateway contracts are aligned — every new DTO field traces to a real backend source, verified during Batch 6's no-fabrication audit.
- G-01's persistence migration applies cleanly against a populated table and is verified, not just written.
- Loading/error/empty/retry behavior for every new UI surface reuses the existing shared components exactly — no new pattern invented anywhere in this scope.
- No fabricated data, contract, or business state is introduced anywhere in the change — including no new "looks real but isn't" presentation (the exact failure mode A-07/G-02 exist to fix elsewhere).
- All existing Step 7 functionality remains intact — full regression suite green, zero degradation to Dashboard, Investigation, Recommendation read, Analytics Trend Analysis, or the `BusinessImpactCompleted` fan-out.
- Backend tests, frontend tests, typecheck, lint, and production build all pass.
- `docker compose config` remains valid.
- Real-service E2E verification passes for every flagged flow (§9).
- Documentation is synchronized at final closure only, per §10 — not per-batch.
- No deferred Phase 11/12/13 or production-hardening capability was accidentally implemented — explicitly checked against the Scope Freeze's DEFER/EXCLUDE list (G-03, G-04, G-06, G-09, editable configuration, authentication, broker/Outbox/retry, Copilot, Evaluation UI) as part of Batch 6's closure review.

---

## Reporting Notes (not part of the architecture, retained for closure reference)

1. **File created:** `docs/architecture/phase-10/STEP_7X_IMPLEMENTATION_ARCHITECTURE.md` (this document). No other file was created or modified. No source code, tests, or project-level documentation were touched. No Git operations were performed.
2. **Batches covered:** all six, as specified — Foundation, Existing-data wiring, Small backend capabilities, UX honesty, Decision-dependent, Diagnostic + verification + closure.
3. **Approved scope covered:** A-01 through A-09 (full field-level design for all nine), G-01 and G-05 (detailed persistence/read-only-config design per Tasks 8–9), G-02 (design), G-08 (decision recorded, zero build work).
4. **Deferred scope confirmed:** G-03, G-04, G-06, G-09, editable/persisted Intelligence Configuration, authentication/RBAC, broker/Outbox/retry, Copilot, Evaluation UI, and every other item on the Scope Freeze's DEFER/EXCLUDE list — none appears anywhere in the Build sections above.
5. **Genuine unresolved implementation decisions surfaced during this pass:**
   - **A-06's exact shape** requires a five-minute vocabulary check (`IssueCategory` enum values vs. `entity_type`/`entity_value`'s actual runtime values) at the start of Batch 3, before implementation — not before this architecture document, since it doesn't block the rest of the batch or any other batch. If that check fails, A-06 reclassifies to G and is pulled from Batch 3 without blocking A-04/A-05.
   - **A-05's exact confidence-band thresholds** are explicitly not invented here (per Task 10's instruction) and must be chosen as a small, explicit design step at the start of Batch 3 implementation, informed by `compute_confidence()`'s discrete six-value range (0/20/40/60/80/100%).
   - **G-07 is resolved, not open:** direct inspection of `ErrorBoundary.tsx` and `DashboardWorkspace.tsx` shows the retry mechanism (`onRetry`/`resetKeys`) was already correctly implemented in a prior "Part 7 rectification." The doc-comment cross-reference in the section error gates (`DashboardSectionErrorGate.tsx` etc.) pointing to "the retry caveat" is stale, not an active defect. No fix batch is needed; Batch 6 only needs to note this at closure (optionally tidy the stale comment, not required for Definition of Done).

Awaiting **"START STEP 7.X IMPLEMENTATION"** before any code, test, or documentation file is modified.