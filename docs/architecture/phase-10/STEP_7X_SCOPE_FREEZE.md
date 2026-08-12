# Phase 10 — Intermediate Step 7.X
# Scope Freeze + Implementation Boundary

**Status:** Decision-gate document. Nothing in the repository has been modified. No implementation has begun.
**Date:** 2026-08-12
**Primary source:** `docs/architecture/phase-10/STEP_7X_CAPABILITY_GAP_INVENTORY.md` (no repository re-scan performed; findings reused as-is, cited by section).

---

## Task 1 — Reconciling the Class-A Count

The inventory's Executive Summary said "13 Class-A candidates" while its consolidated register (§19) enumerated fewer top-level entries with ambiguous sub-item counting (explicitly noted as unresolved in that section: *"11–13. (Sub-items of #1 and #2 above are tracked as one build task each per endpoint group, not separately enumerated.)"*). That was an inconsistency, not a real count. Resolving it by applying one rule — **one entry per genuinely independent implementation unit, neither split for volume nor merged for brevity** — produces exactly **9 units**:

| ID | Finding | Inventory ref |
|---|---|---|
| A-01 | Dashboard Supporting Evidence → real anomaly_service trend data | §4, §7, §16 |
| A-02 | Administration Platform Overview → real service health aggregation | §4, §11, §16 |
| A-03 | Partial-failure `warnings` rendering (Dashboard + Investigation) | §4, §8, §15, §16 |
| A-04 | Dashboard Recommended Focus — resolve structural always-empty state | §4, §7 |
| A-05 | Business Impact confidence classifier | §4, §8 |
| A-06 | NLP-service incident-scoped enrichment endpoint | §4, §8 |
| A-07 | Recommendation Decision & Lifecycle — UX honesty correction | §9, §17 |
| A-08 | Analytics Executive Overview — real rollup or honest placeholder | §10, §17 |
| A-09 | Dashboard filter-scope setter normalization | §7, §16 |

**Why A-01/A-02 are not split per endpoint** (the source of the original overcount): each is one Gateway aggregation route calling multiple existing backend endpoints as a single cohesive section — Supporting Evidence is one frontend section backed by four `anomaly_service` trend endpoints called together, and Platform Overview is one frontend section backed by nine `/health` endpoints called together. Splitting by endpoint would create artificial sub-tasks with no independent product value.

**Why A-07 combines Decision and Lifecycle** (not two entries): both share one root cause (no backend domain model, both fabricated the same way), one fix pattern (`FutureCapabilityPlaceholder`), and Recommendation Lifecycle is structurally gated on Decision existing first ("Decision Before Lifecycle," Phase 10 Step 4). They ship as one PR by construction.

**Why A-03 is not split into two entries** (Dashboard warnings vs. Investigation warnings): identical shared component, identical DTO field, identical fix — two integration points, one implementation unit.

No entry was merged that has independent value on its own — A-04, A-05, A-06, A-08, A-09 each stand alone because they touch different services/sections with no shared component or sequencing dependency.

---

## Task 2 — Classification of Every Finding (carried forward, no reclassification without cause)

No G finding is silently converted to A. Every A/G finding restates its evidence and, for G items, a proposed decision with consequences (Task 3). The full B/C/D/E/F register is unchanged from the inventory §19 and is not reproduced in full here — see the inventory for the complete list. The items load-bearing for this scope freeze are:

**A (9 — Task 1 above).**
**G (9 — Task 3 below).**
**B, C, D, E, F** — unchanged from inventory §19; none are candidates for this scope freeze by definition, and none are re-litigated here.

---

## Task 3 — Decision Gate

Nine items. For each: finding → why it needs a decision → minimal viable decision → recommended option → frontend/backend impact → Step 7.X eligibility → deferability.

### G-01 — Recommendation Decision/Lifecycle persistence
- **Finding:** No decision/status/approve/reject/defer field exists anywhere in `recommendation_service`'s domain model (verified by full-service grep, inventory §9).
- **Why it needs a decision:** Requires choosing a schema shape and deciding what "decision" means as a persisted concept — not a wiring task.
- **Minimal viable decision:** Add a nullable `decision` enum (`pending` / `approved` / `rejected` / `deferred`) plus `decision_note` and `decided_at` as new columns on the existing `RecommendationEntity` — no new service, no new bounded context, no "decision-owner/actor" field (that requires real identity, which doesn't exist until Phase 13 auth — see G-06). Exposed via one new `PATCH` endpoint, Gateway-routed.
- **Recommended option:** Adopt the minimal decision (extend existing entity); explicitly exclude decision-owner attribution until Phase 13.
- **Impact — Frontend:** Recommendation workspace's Decision section becomes real (replacing the fabricated constant); Recommendation Lifecycle can then honestly reflect "decision exists" per its already-coded structural rule.
- **Impact — Backend:** one migration (3 nullable columns), one new endpoint, one new Gateway route + DTO field.
- **Step 7.X eligible:** Yes, if the minimal-decision option is approved — this is a genuine Phase 10 product capability, not infrastructure.
- **Deferable without blocking the rest:** Yes. A-07 (the UX-honesty placeholder fix) ships independently of this decision either way.

### G-02 — Analytics narrative-section honesty treatment
- **Finding:** Pattern Discovery, Organizational Insights, and Strategic Opportunities render a specific fabricated narrative with the same visual confidence as real Trend Analysis data, contradicting the documented "honest future-capability state" claim (inventory §10, §17).
- **Why it needs a decision:** Two legitimate paths exist — wrap as an honest placeholder (matching Recommendation Effectiveness's existing precedent) or explicitly document the current hardcoded content as an intentional "vision preview." Both are cheap; the choice is a product-presentation call, not an engineering one.
- **Minimal viable decision:** Choose (a) wrap all three in `FutureCapabilityPlaceholder`, or (b) keep as-is but add explicit "illustrative example" labeling.
- **Recommended option:** (a) — wrap in `FutureCapabilityPlaceholder`, for consistency with Recommendation Effectiveness and the platform's established honesty discipline.
- **Impact — Frontend only:** swap the three components' content-rendering strategy; zero backend change.
- **Step 7.X eligible:** Yes — pure UX-honesty, zero backend risk, no new contract.
- **Deferable:** Not blocking anything else; can ship as soon as decided.

### G-03 — `RecommendationStatisticsService` surfacing/ownership
- **Finding:** Real, cheap backend aggregation (counts/averages by category/priority) exists and is completely unsurfaced (inventory §10, §16).
- **Why it needs a decision:** Ambiguous whether it belongs in Analytics (as a new "Recommendation Activity" mini-section) — and doing so risks a user conflating raw activity counts with the still-placeholder "Recommendation Effectiveness" sitting in the same workspace.
- **Minimal viable decision:** Surface it now under Analytics with an explicit "activity, not effectiveness" label, or leave unsurfaced.
- **Recommended option:** Leave unsurfaced for now. The conflation risk with the adjacent effectiveness placeholder outweighs the marginal value of exposing simple counts; revisit alongside G-01 once Recommendation Lifecycle is real and a genuine "activity" framing has more context to sit next to.
- **Impact:** None if deferred.
- **Step 7.X eligible:** Low priority — recommend defer.
- **Deferable:** Yes, cleanly.

### G-04 — Root Cause confirm/reject/refresh (write capability)
- **Finding:** Real, implemented mutation endpoints exist in `root_cause_service`, entirely unsurfaced to Gateway or frontend (inventory §8, §16).
- **Why it needs a decision:** This would be Investigation's first *write* capability — Step 7 established a read-only integration precedent for this workspace. It also raises the same "who did this" attribution problem as G-01's decision-owner, and there is currently no identity system to attribute an action to (see G-06).
- **Minimal viable decision:** Is analyst confirm/reject/refresh in scope for Step 7.X now, or does it wait until attribution is possible?
- **Recommended option:** Defer. Same identity gap as G-01's excluded decision-owner field, plus a larger interaction-model change than the rest of Step 7.X's read-wiring focus.
- **Impact:** None now.
- **Step 7.X eligible:** No — recommend keeping as G, revisit post-Phase-13.
- **Deferable:** Yes, cleanly.

### G-05 — Administration Intelligence Configuration (live config)
- **Finding:** `business_impact_service`'s weighting/scoring constants (`weighting.py`, `scoring.py`) are real, hardcoded, module-level Python constants — not DB-backed, no config-management layer exists (inventory §11, §14).
- **Why it needs a decision:** Turning frozen, ARB-003-governed engine constants into live *editable* configuration would reopen a frozen domain-engine decision and requires a versioning/safety design outside Step 7.X's scope.
- **Minimal viable decision:** Does Step 7.X touch the engine at all, or build only a **read-only** "current configuration values" display sourced directly from the existing constants (no persistence, no write path)?
- **Recommended option:** Read-only display only. A thin new `GET` endpoint exposes the existing constants verbatim; zero change to `business_impact_service`'s engine logic; matches Administration's own established UX principle ("inspection is the permanent default state").
- **Impact — Frontend:** Intelligence Configuration section shows real current values instead of hardcoded example values; the existing "editing affordance" pattern stays visually present but remains non-functional (matches Administration's frozen UX spec — inspection first, editing reachable only through an explicit toggle that currently persists nothing).
- **Impact — Backend:** one new read-only endpoint in `business_impact_service` (or a Gateway-side static read if simpler); no schema change, no migration.
- **Step 7.X eligible:** Yes, if scoped strictly to read-only. Editable/persisted config is excluded from this decision and remains future work.
- **Deferable:** The read-only version is safe to build now; full editable config should not be attempted in Step 7.X under any option.

### G-06 — Administration User & Access Management
- **Finding:** No user/role/permission model anywhere in the repository (inventory §11, §12).
- **Why it needs a decision:** Directly borders the Phase 13 JWT/RBAC deliverable; any partial user model built now risks conflicting with or duplicating the eventual real auth design.
- **Minimal viable decision:** None required — there is no safe read-only subset here (unlike G-05) because there is no real user data anywhere to read.
- **Recommended option:** Defer fully to Phase 13. No Step 7.X action.
- **Impact:** None.
- **Step 7.X eligible:** No.
- **Deferable:** Yes, with no dependency on the rest of Step 7.X.

### G-07 — Section error-gate retry caveat
- **Finding:** `DashboardSectionErrorGate.tsx`, `InvestigationSectionErrorGate.tsx` (and the Recommendation/Analytics equivalents) carry doc comments referencing an unresolved "Step 7 hardening item," with no further detail available in-repo (inventory §8, §15).
- **Why it needs a decision:** Insufficient evidence to know what the actual defect is — cannot be safely fixed (or safely excluded) without a targeted look first.
- **Minimal viable decision:** Authorize one small, targeted diagnostic read of the actual `ErrorBoundary`/`onRetry`/`resetKeys` code path referenced by these comments (a single-file investigation, not a repository re-audit) to determine what the caveat actually is.
- **Recommended option:** Approve the diagnostic step as part of Step 7.X's verification batch; classify the underlying finding as A (real bug, fix now) or E (documented future hardening, no action) only after that diagnosis — do not guess now.
- **Impact:** None until diagnosed; the diagnosis itself is near-zero-cost.
- **Step 7.X eligible:** The diagnostic step, yes. The fix, contingent on what's found.
- **Deferable:** The diagnosis should happen inside Step 7.X (cheap, resolves ambiguity); it does not block any other batch and can run in parallel or last.

### G-08 — Evaluation Service UI surface
- **Finding:** `evaluation_service` has a full 5-endpoint REST API, zero consumers, and no Evaluation workspace was ever scoped in the five-workspace architecture (inventory §13).
- **Why it needs a decision:** Ambiguous by omission, not by conflict — `evaluation_service` is architecturally described as an independent, out-of-band Intelligence Assurance Service (Phase 8), which is arguably meant to *observe* the platform rather than be observed by end users through a workspace.
- **Minimal viable decision:** A single explicit statement: no Evaluation UI is planned in the Phase 10 lineage; its eventual consumer is future tooling/Copilot (Phase 12), not a workspace.
- **Recommended option:** Adopt that statement now, closing the ambiguity at zero implementation cost.
- **Impact:** None — this decision produces no build work.
- **Step 7.X eligible:** The decision itself, yes (free). No follow-on work.
- **Deferable:** N/A — recommend deciding now since it costs nothing and prevents future re-litigation.

### G-09 — Dashboard full filter dimensions (region/BU/product/user)
- **Finding:** No data model exists for these dimensions anywhere in `anomaly_service`; the Gateway correctly rejects them today rather than fake-filtering (inventory §7, §16, §23).
- **Why it needs a decision:** Real dimensional filtering requires new schema-level work on `anomaly_service`'s trend/incident data model — this is "a larger new backend capability," which the Step 7.X principle explicitly deprioritizes relative to wiring existing capability.
- **Minimal viable decision:** Is dimensional filtering in scope for Phase 10 Step 7.X, or does it wait for a future data-modeling initiative?
- **Recommended option:** Defer. No evidence anywhere in the inventory that these dimensions are already collected upstream (would require new fields in ingestion/complaint data, not just anomaly_service) — this is new capability, not unwired capability, and falls outside Step 7.X's stated priority order (wiring existing data first, small missing pieces second, larger new capability only last).
- **Impact:** None if deferred; current honest-rejection behavior (Class C) is correct and stays as-is.
- **Step 7.X eligible:** No.
- **Deferable:** Yes, cleanly — A-09 (setter normalization) already resolves the leftover frontend inconsistency without needing this decision.

---

## Task 4 — Final Step 7.X Scope

### BUILD NOW
(Class A, no blocking decision, ready to plan into batches)

1. A-01 — Dashboard Supporting Evidence → real trend data
2. A-02 — Administration Platform Overview → real service health
3. A-03 — Partial-failure `warnings` rendering (Dashboard + Investigation)
4. A-04 — Dashboard Recommended Focus — resolve structural emptiness
5. A-05 — Business Impact confidence classifier
6. A-06 — NLP-service incident-scoped enrichment endpoint
7. A-07 — Recommendation Decision & Lifecycle UX honesty correction
8. A-08 — Analytics Executive Overview — real rollup or honest placeholder
9. A-09 — Dashboard filter-scope setter normalization

### DECISION REQUIRED
(Recommended options given in Task 3; each awaits explicit approval before any implementation)

| ID | Recommended option | If approved, becomes |
|---|---|---|
| G-01 | Minimal decision persistence on `RecommendationEntity` (no decision-owner) | Build item, Batch 5 |
| G-02 | Wrap Analytics narrative sections in `FutureCapabilityPlaceholder` | Build item, Batch 4 |
| G-03 | Leave `RecommendationStatisticsService` unsurfaced | No build (defer) |
| G-04 | Defer Root Cause mutation surfacing | No build (defer) |
| G-05 | Read-only Intelligence Configuration display only | Build item, Batch 5 |
| G-06 | Defer fully to Phase 13 | No build (defer) |
| G-07 | Approve one targeted diagnostic read | Diagnostic task, Batch 6; fix TBD |
| G-08 | Adopt "no Evaluation UI planned" statement | No build (decision only, zero cost) |
| G-09 | Defer full filtering; keep honest rejection | No build (defer) |

### DEFER / EXCLUDE
(Must not be implemented in Step 7.X — reasons stated per inventory classification)

- Recommendation Effectiveness/Outcome tracking — **already implemented as honest placeholder; underlying capability is Phase 11+ (ARB-002 long-term vision)**
- `RecommendationsGenerated` / `EvaluationCompleted` real consumption — **insufficient current capability / by design, future subscriber**
- `evaluation_service` UI — **decision made in G-08: none planned**
- Recommendation list/statistics/generation/incident-scoped read endpoints as a frontend feature — **future phase (Recommendations list/history view), not current-scope**
- Administration Data Sources & Integrations — **insufficient current capability, net-new persistence**
- Administration Audit & Change History — **insufficient current capability, net-new persistence**
- Administration User & Access Management — **Phase 13 (production hardening / auth)**
- Administration Intelligence Configuration *editable/persisted* form — **architectural decision not justified for Step 7.X (G-05 approves read-only only)**
- Root Cause confirm/reject/refresh — **architectural decision deferred (G-04)**
- `RecommendationStatisticsService` surfacing — **architectural decision deferred (G-03)**
- Dashboard region/businessUnit/productScope/userScope real filtering — **architectural decision deferred (G-09); insufficient current capability**
- Authentication/RBAC (all forms) — **Phase 13, production hardening**
- Message broker, Outbox, durable retry, event replay — **production hardening, explicitly excluded**
- `copilot_service` — **Phase 12, already correctly scaffolded-only**
- Everything already classified B (already implemented correctly) — **no action, not a gap**
- Everything already classified C (intentionally presentation-only/honest placeholder) other than G-02's chosen items — **already correct, no action**

---

## Task 5 — Dependency Order

Grouped into six meaningful batches (not artificially split further):

**Step 7.X-1 — Foundation / shared prerequisites**
- Build the shared partial-failure warnings UI pattern (used by A-03 in two workspaces).
- Normalize Dashboard scope-filter context setters (A-09).
- Adopt the G-08 zero-cost decision ("no Evaluation UI planned").
- *No backend dependency; unblocks nothing else but has no dependency on anything else either — safe to do first.*

**Step 7.X-2 — Existing backend → frontend wiring (no new backend code)**
- A-01 — Dashboard Supporting Evidence (wires 4 existing `anomaly_service` endpoints).
- A-02 — Administration Platform Overview (wires 9 existing `/health` endpoints).
- *Depends on: nothing new — pure Gateway aggregation + frontend consumption of already-existing backend endpoints.*

**Step 7.X-3 — Small backend capability additions**
- A-05 — Business Impact confidence classifier (new module in `business_impact_service`, mirroring `root_cause_service`'s existing pattern).
- A-06 — NLP-service incident-scoped enrichment endpoint (new query capability in `nlp_service`).
- A-04 — Dashboard Recommended Focus (small derivation logic, likely in `dashboard_aggregator.py` or a new `anomaly_service`/`business_impact_service` capability — exact ownership to be confirmed at implementation time, not a blocking ambiguity here since it doesn't require a product decision, only an engineering placement choice).
- *Depends on: nothing from Batch 1/2; can run in parallel with them.*

**Step 7.X-4 — UX honesty / placeholder corrections**
- A-07 — Recommendation Decision & Lifecycle placeholder correction.
- A-08 — Analytics Executive Overview real rollup or placeholder.
- G-02 (if approved) — wrap Analytics narrative sections in `FutureCapabilityPlaceholder`.
- *Depends on: nothing technically, but sequenced after Batches 2–3 so any newly-real data (e.g., A-08's rollup) can use it if the decision favors a real computation over a placeholder.*

**Step 7.X-5 — Decision-dependent capabilities (gated on explicit approval)**
- G-01 (if approved) — minimal Recommendation decision persistence.
- G-05 (if approved) — read-only Intelligence Configuration display.
- *Depends on: explicit sign-off from Task 4's "Decision Required" list. Not started until approved.*

**Step 7.X-6 — Cross-system verification**
- G-07's diagnostic read (can run any time before this batch closes).
- Full regression suite (backend + frontend), typecheck, lint, production build, `docker compose config` validation.
- Real-service end-to-end verification for every Batch 1–5 change, following the same discipline Step 7 already established.
- Documentation sync (`docs/PROJECT_STATUS.md`, `docs/CHANGELOG.md`, `ROADMAP.md` if applicable) — performed only at final closure, not per-batch.

---

## Task 6 — Frontend + Backend Completeness (BUILD NOW items only)

**A-01 — Dashboard Supporting Evidence**
- Frontend: `frontend/src/workspaces/dashboard/components/SupportingEvidence/SupportingEvidence.tsx` (replace `DEFAULT_EVIDENCE_ITEMS` with fetched data); `api/dashboardApi.ts`; `hooks/useDashboardData.ts`; `api/viewModel.ts` (new mapped fields).
- Backend: no new backend code — `anomaly_service/app/api/trends.py` (`/trends/categories`, `/trends/regions`, `/trends/sentiment`, `/trends/urgency`) already exist.
- Gateway: extend `dashboard_aggregator.py` to call the four endpoints; add corresponding fields to `schemas/dashboard.py`.
- Integration: Dashboard → `dashboardApi.ts` → `GET /api/v1/dashboard` → `dashboard_aggregator.py` (new calls) → `anomaly_service` (existing) → response → `SupportingEvidence.tsx`.
- Dependency: none.

**A-02 — Administration Platform Overview**
- Frontend: `frontend/src/workspaces/administration/components/.../PlatformOverview.tsx`; new `administration/api/` directory (currently absent — first API module for this workspace); new hook for fetching.
- Backend: no new backend code — every service's existing `/health` endpoint.
- Gateway: **new** `backend/services/gateway_service/app/api/administration.py`, new aggregator, new schema — this is the first Gateway surface for Administration.
- Integration: Administration → new `administrationApi.ts` → `GET /api/v1/administration/overview` (new route) → new aggregator fan-out to 9 `/health` endpoints → response → `PlatformOverview.tsx`.
- Dependency: none, but is the largest single unit in Batch 2 since it introduces a new Gateway namespace.

**A-03 — Partial-failure warnings rendering**
- Frontend: new shared component (e.g., a `WarningsBanner`) in `frontend/src/shared/components/`; wired into `DashboardWorkspace.tsx` and `InvestigationsWorkspace.tsx`, reading the already-mapped `warnings` field from each `viewModel.ts`.
- Backend: none — Gateway already populates `warnings` correctly.
- Integration: existing fetch → existing `viewModel.warnings` (already populated) → new shared component render. Purely additive frontend work.
- Dependency: none.

**A-04 — Dashboard Recommended Focus**
- Frontend: `RecommendedFocus.tsx` — remove the always-`[]` assumption once real data arrives; `viewModel.ts` update.
- Backend: `dashboard_aggregator.py:192` currently hardcodes `focusAreas=[]` — needs a real derivation. Placement to be decided at implementation time (aggregator-level composition from existing incident/recommendation data already fetched for other sections, vs. a new small domain capability) — this is an engineering choice, not a product decision, since no new data source is required, only new composition logic from data already being fetched.
- Integration: Dashboard → `dashboard_aggregator.py` (new derivation from already-fetched incidents/recommendations) → `RecommendedFocus.tsx`.
- Dependency: benefits from being sequenced after A-01/A-02 (same aggregator file) but does not require them.

**A-05 — Business Impact confidence classifier**
- Backend: new `backend/services/business_impact_service/app/domain/confidence.py` (mirrors `root_cause_service/app/domain/confidence.py`'s existing pattern) — pure domain addition, no engine/scoring change, ARB-008-compliant (stage-specific, no shared scale).
- Gateway: `gateway_service/app/core/confidence.py` extended to map Business Impact's own bands (separately from Root Cause's, preserving ARB-008); `investigation_aggregator.py:98-109` stops hardcoding `None`.
- Frontend: `BusinessImpact.tsx` already has a `confidenceLevel` prop wired — this becomes populated automatically once the Gateway stops suppressing it.
- Integration: `business_impact_service` (new classifier) → Gateway (new band mapping) → `investigation_aggregator.py` → `BusinessImpact.tsx` (already wired).
- Dependency: none.

**A-06 — NLP-service incident-scoped enrichment endpoint**
- Backend: new endpoint in `backend/services/nlp_service/app/api/enrichments.py` (e.g., `GET /enrichments?incident_id=`), requiring a read path from incident → complaints → enrichments (respecting DATA-002 service-local read models — no ORM import from other services).
- Gateway: `investigation_aggregator.py:148-156` starts calling the new endpoint and emitting `"NLP Intelligence"` evidence (the schema literal already exists, currently dead — inventory §16).
- Frontend: `Evidence.tsx`/`EvidenceGroup.tsx` already render whatever `EvidenceSource` values arrive — no frontend change needed beyond verifying rendering of the new source type.
- Integration: `nlp_service` (new endpoint) → `investigation_aggregator.py` (new call) → existing `Evidence.tsx` rendering.
- Dependency: requires care around DATA-002 (service-local read models) — flagged in Task 7.

**A-07 — Recommendation Decision & Lifecycle UX correction**
- Frontend: `RecommendationsWorkspace.tsx:19-22` (remove the fabricated `DECISION` constant), `Decision.tsx`, `DecisionSummary.tsx`, `RecommendationLifecycle.tsx`, `LifecycleSummary.tsx` — swap to `FutureCapabilityPlaceholder` (same component already used by Alternative Options/Expected Outcome/Risk Assessment).
- Backend: none for this UX-only version (independent of G-01).
- Integration: purely frontend; no Gateway/backend change.
- Dependency: none. If G-01 is separately approved, this becomes the visual foundation the real Decision UI replaces in Batch 5.

**A-08 — Analytics Executive Overview**
- Frontend: `ExecutiveOverview.tsx:7-11` — replace hardcoded `OBSERVATIONS` strings with a real computation from already-fetched `AnalyticsViewModel` data (volume-trend point count, category count — both already present in `AnalyticsResponse`), or wrap in `FutureCapabilityPlaceholder` if the real-rollup option is not preferred.
- Backend/Gateway: none — uses data already being fetched by `useAnalyticsData.ts` for Trend Analysis.
- Integration: purely a frontend view-model computation change.
- Dependency: none.

**A-09 — Dashboard filter-scope setter normalization**
- Frontend only: `DashboardContext.ts` / `DashboardContextProvider.tsx` — add the missing `setProductScope`/`setUserScope` for symmetry with existing `setRegion`/`setBusinessUnit` (none of the four currently have a UI caller either — this is a consistency fix, not new filtering capability; see G-09 for why real filtering itself is deferred).
- Backend/Gateway: none.
- Dependency: none.

---

## Task 7 — Architecture Preservation Confirmation

Every BUILD NOW (A-01…A-09) and every recommended-approve DECISION REQUIRED item (G-01, G-02, G-05, G-08) was checked against the frozen constraints:

| Constraint | Status | Notes |
|---|---|---|
| Gateway/BFF boundary (frontend never calls backend directly) | ✅ Preserved | A-02 adds a new Gateway namespace (`administration.py`) rather than exposing `/health` endpoints directly to the frontend. |
| Three-model-layer separation (domain/persistence/DTO) | ✅ Preserved | A-05's new classifier and A-06's new endpoint follow the same domain-layer pattern already established by `root_cause_service`. |
| No-fake-contract rule | ✅ Preserved | Every BUILD NOW item wires or exposes *real* data; none introduces a fabricated field. A-07/A-08/G-02 remove fabrication rather than adding it. |
| Service ownership (DATA-002 — no cross-service ORM imports) | ✅ Preserved, flagged for care | A-06's incident-scoped enrichment endpoint must resolve incident→complaint→enrichment without importing another service's ORM models — service-local read models only, per existing precedent. |
| `incident_id` ≠ `event_id` distinction | ✅ Not touched | No BUILD NOW or approved-decision item modifies event contracts. |
| `recommendation_id` ≠ `incident_id` distinction | ✅ Preserved | G-01's minimal decision adds columns to the existing `RecommendationEntity`, keeping both identifiers exactly as they are; no new identifier is introduced. |
| ARB-008 stage-specific confidence | ✅ Preserved by construction | A-05 explicitly creates Business Impact's *own* confidence classifier, structurally separate from Root Cause's — the same non-negotiable separation the inventory verified is already respected. |
| Internal event isolation (`/internal/events/*` never Gateway-routed) | ✅ Not touched | No BUILD NOW or approved-decision item touches the event layer. |
| `BusinessImpactCompleted` parallel fan-out | ✅ Not touched | Unaffected by any item in this scope. |
| Phase 11/12/13 boundaries | ✅ Preserved | Auth (G-06), broker/Outbox/retry, Copilot, and observability platform work are all in DEFER/EXCLUDE; G-05 stops explicitly short of building a config-persistence/versioning layer that would border Phase 13. |

No proposed capability was found to conflict with a frozen decision. Where a proposal *could* have drifted toward one (G-01's decision-owner field, G-04's write-attribution, G-05's editable/persisted config, G-06's user model), the recommended minimal option explicitly excludes the conflicting part and defers it — this is why those remain G rather than being resolved into A.

---

## Task 8 — Final Implementation Plan

# Phase 10 — Step 7.X — Scope Freeze

## 1. Final approved capabilities (BUILD NOW)
A-01 Dashboard Supporting Evidence · A-02 Administration Platform Overview · A-03 Partial-failure warnings rendering · A-04 Dashboard Recommended Focus · A-05 Business Impact confidence classifier · A-06 NLP incident-scoped enrichment · A-07 Recommendation Decision & Lifecycle UX correction · A-08 Analytics Executive Overview · A-09 Dashboard filter-scope setter normalization.

## 2. Final decision-required capabilities
G-01 Recommendation decision persistence (minimal) · G-02 Analytics narrative-section placeholder treatment · G-03 RecommendationStatistics surfacing (recommend: no) · G-04 Root Cause mutation surfacing (recommend: no) · G-05 Intelligence Configuration read-only display · G-06 User & Access Management (recommend: no) · G-07 Error-gate retry caveat diagnosis · G-08 Evaluation UI decision (recommend: adopt "none planned" now, zero cost) · G-09 Full dashboard filtering (recommend: no).

## 3. Explicitly deferred capabilities
RecommendationStatisticsService surfacing (G-03) · Root Cause confirm/reject/refresh (G-04) · Administration User & Access Management (G-06) · Administration Intelligence Configuration editable/persisted form · Dashboard full dimensional filtering (G-09) · Recommendation list/statistics/generation read endpoints as a frontend feature · Administration Data Sources & Integrations · Administration Audit & Change History.

## 4. Explicitly excluded future-phase capabilities
Recommendation Effectiveness/Outcome tracking (Phase 11+, ARB-002) · `RecommendationsGenerated`/`EvaluationCompleted` real consumption · Evaluation Service UI (decided: none planned) · Authentication/RBAC (Phase 13) · Message broker/Outbox/durable retry/event replay (production hardening) · `copilot_service` (Phase 12) · mTLS/service mesh/broader production security hardening.

## 5. Implementation batches
Step 7.X-1 Foundation (shared warnings component, filter-setter normalization, G-08 decision) → Step 7.X-2 Existing-data wiring (A-01, A-02) → Step 7.X-3 Small backend additions (A-05, A-06, A-04) → Step 7.X-4 UX honesty corrections (A-07, A-08, G-02 if approved) → Step 7.X-5 Decision-dependent work (G-01, G-05, only if approved) → Step 7.X-6 Cross-system verification (G-07 diagnosis, full regression, documentation sync).

## 6. Dependencies
Batches 1–3 are mutually independent and may run in any order or in parallel. Batch 4 is sequenced after 2–3 only for convenience (so A-08 can use newly-available data patterns if desired), not by hard requirement. Batch 5 is gated entirely on explicit approval of G-01/G-05 from Task 4's decision table — no work in Batch 5 starts before that approval. Batch 6 closes the step and depends on all prior batches being functionally complete.

## 7. Architecture constraints
All nine preserved constraints from Task 7 apply unconditionally to every batch. The one item requiring engineering care during implementation (not a blocking decision) is A-06's adherence to DATA-002 (service-local read models, no cross-service ORM imports) when resolving incident→complaint→enrichment.

## 8. Verification requirements
For every batch: backend and frontend automated test suites green, mypy/typecheck clean, lint clean, production build green, `docker compose config` valid. For Batches 2–5 specifically: real-service end-to-end verification against real PostgreSQL and real HTTP requests (not mocks), matching the discipline Step 7 already established, including for any new Gateway routes (A-02, G-01, G-05) and any new backend endpoints (A-05, A-06).

## 9. Definition of Done
A Step 7.X item is done only when: (a) frontend implementation is complete and matches the frozen Phase 10 workspace UX specifications; (b) backend implementation (where applicable) is complete with no changes to frozen domain engines beyond the explicitly-scoped additions (e.g., A-05's new classifier module, never touching `scoring.py`/`weighting.py`); (c) API/DTO contracts are defined and match the Gateway's existing error-envelope/correlation-ID/timeout conventions; (d) persistence changes (only G-01 if approved) ship with a migration and preserve `recommendation_id`/`incident_id` distinctness; (e) the full Frontend→API→Gateway→Backend→Persistence/Event→Response→Frontend chain is integrated and verified, not just unit-tested in isolation; (f) loading/error/empty/retry states reuse the existing shared components (`ErrorBoundary`, section error gates, skeleton states) with no new UX pattern invented; (g) automated tests, typecheck, lint, and production build are all green with no regressions to any Step 1–7 capability; (h) no fabricated data or fake contract was introduced anywhere in the change; (i) `docs/PROJECT_STATUS.md`, `docs/CHANGELOG.md`, and `docs/DECISIONS.md` (for any accepted G-item decision) are updated **only at final Step 7.X closure**, not per-batch, mirroring how Step 7's own documentation sync was handled.

## 10. Final Step 7.X scope statement
Step 7.X is scoped to nine independently-implementable capabilities (A-01…A-09) that wire already-real backend data, add small and clearly-bounded backend capabilities, or correct UX honesty violations — plus up to four decision-gated capabilities (G-01, G-02, G-05, G-08) that become buildable only after explicit approval of the minimal-viable decisions proposed in Task 3. Five further items (G-03, G-04, G-06, G-09, and the editable-config portion of G-05) are recommended for deferral, and a broad set of Phase 11–13 and production-hardening capabilities remain explicitly excluded. This scope preserves every frozen architectural constraint verified in Task 7. **No implementation begins until this scope freeze is explicitly approved.**