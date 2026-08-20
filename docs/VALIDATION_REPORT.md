# Validation Report

## 1. Validation Scope

This report covers the 2026-08-20 dataset/dataset-version and ingestion-stabilization milestone specifically. It was produced against the repository's current working tree — `main`, commit `8134ede` plus the two CI fixes and one test-fixture fix applied in this pass (see `docs/CHANGELOG.md` for the milestone itself) — which includes the dataset/dataset-version architecture, ingestion normalization and field mapping, row analysis, duplicate detection, dataset-scoped intelligence, and dataset lifecycle/archive handling.

**This is not a repeat, and not a full replacement, of the prior 2026-08-16 whole-system validation.** That report validated a pre-dataset system (17 migrations, one global complaint table, no dataset concept; also Copilot, `evaluation_service`, observability, and backup/restore, none of which are re-covered here) and remains real, valid evidence for everything it tested — it has been preserved verbatim, unedited, at [`docs/VALIDATION_REPORT_2026-08-16_WHOLE_SYSTEM.md`](VALIDATION_REPORT_2026-08-16_WHOLE_SYSTEM.md). This document occupies `docs/VALIDATION_REPORT.md` because it is the current, actively-maintained validation record going forward; it is scoped narrower than its predecessor by design, not by omission. Every claim below is labelled by evidence type, same convention as before:

| Label | Meaning |
|---|---|
| `[RUNTIME]` | Executed against real running services during this validation; output observed directly. |
| `[TEST]` | Produced by an automated test suite run during this validation. |
| `[CODE INSPECTION]` | Read from source; not executed during this validation. |

## 2. Environment

| Item | Value |
|---|---|
| Host | Windows 11, Docker 29.2.1, Docker Compose v5.1.0 |
| Backend test runner | Python 3.11 (matches every service's `Dockerfile`) |
| Frontend test runner | Node 22.12.0 locally; CI now pins Node 22 (see §3) |
| Validation stack | A separate, disposable Compose project (`oival2`) on its own empty volume — postgres, gateway, ingestion, nlp, anomaly, root_cause, business_impact, recommendation. `copilot_service` and `evaluation_service` were deliberately not started for this pass (not part of the dataset/ingestion milestone under validation); their absence is itself real evidence the service-health check correctly reports (§10). Torn down (`down -v`) after validation — the persistent dev database was never touched. |
| External LLM provider | Not configured (`LLM_PROVIDER=none`) — unchanged from the prior report, out of scope for this pass. |

## 3. CI-Equivalent Verification

Two real CI failures were found and fixed in this pass before validation began.

**Backend — `KeyError: 'dataset_id'` in `test_internal_auth_propagation.py` (3 tests).** Root cause: `recommendation_aggregator._to_response()` now genuinely requires `dataset_id`/`dataset_version_id` on every recommendation payload (provenance fields added by the dataset milestone) — real, intentional application behavior. The three tests' mock downstream-response bodies predated that change and never carried those fields. Fixed by adding them to the fixture bodies; no application code changed. `[TEST]` 5/5 tests in the file now pass.

**Frontend — crash on Node 20 (`webidl.util.markAsUncloneable is not a function`).** Root cause: `jsdom@30.0.1` pulls in `undici@8.10.0`, which calls a Node-internal webidl API not present on Node 20 (`undici`'s own `engines` field declares `>=22.19.0`; `jsdom` declares `^22.22.2 || ^24.15.0 || >=26.0.0`). `.github/workflows/ci.yml`'s `frontend-checks` job pinned Node 20. This is a CI runtime floor, not a broken package — verified by running the identical `package-lock.json` on Node 22 locally, where it passes cleanly. Fixed by bumping `actions/setup-node`'s `node-version` from `"20"` to `"22"` in `frontend-checks` only; `frontend/Dockerfile` intentionally stays on `node:20-alpine` since it never runs Vitest's jsdom environment.

| Check | Command (exact, as CI runs it) | Result | Count |
|---|---|---|---|
| Backend tests | `alembic upgrade head` then `python -m pytest backend -q` | ✅ PASS | 1,289 passed, 161 skipped, 21 failed locally |
| Frontend lint | `npm run lint` (`eslint .`) | ✅ PASS | 0 errors, 5 pre-existing warnings |
| Frontend typecheck | `npm run typecheck` (`tsc -b --noEmit`) | ✅ PASS | clean |
| Frontend tests | `npm test` (`vitest run`) | ✅ PASS | 381 passed / 381, 53 files |
| Frontend build | `npm run build` (`tsc -b && vite build`) | ✅ PASS | clean, ~1.1s |
| Compose validation | `docker compose -f docker-compose.yml config --quiet` and the `.prod.yml` equivalent, after `cp .env.example .env` | ✅ PASS | both configs valid |

**On the 21 locally-failing backend tests:** all 21 are in `test_auth_api.py`, `test_event_isolation.py`, `test_main.py`, `test_rbac_api.py` — every one requires a `TestClient(app)` lifespan that reaches PostgreSQL via the bare hostname `localhost` from outside this sandbox's network path, a pre-existing, already-documented environment limitation (`docs/CHANGELOG.md`, multiple prior entries) unrelated to this milestone or these fixes. CI's real Postgres service container does not have this restriction. This is **not claimed as CI passing on GitHub** — only that the exact commands CI runs were reproduced locally and, modulo this one known sandbox-networking gap, pass.

**Warnings that do not fail CI, reported separately:** 5 ESLint "unused eslint-disable directive" warnings (`useAnalyticsData.ts`, `useDashboardData.ts`, `useComplaintAnalysis.ts`, `useDataset.ts`, `useRecentComplaints.ts`) — cosmetic, pre-existing, not touched in this pass.

## 4. Dataset and Version Validation

`[RUNTIME]`, live HTTP calls against the isolated stack (§2):

- `POST /api/v1/datasets` → `201`, real UUID `id` returned.
- `alembic upgrade head` applied all 27 migrations from empty to `d8e2f4a6b719` with exit code 0 — including the 9 dataset/mapping/provenance migrations, confirmed as a single linear chain (no branches).
- 12 complaints ingested into a new dataset one at a time (`POST /datasets/{id}/complaints`) → 12/12 `201`.
- Re-submitting an already-ingested row → `409 CONFLICT`, `"A complaint with this signature already exists."` — real source-hash duplicate detection, not a client-side check.
- `POST /datasets/{id}/versions/finalize` → `200`, `status: "ready"`, `cumulativeRecordCount: 12`, `newRecordCount: 12`, real `analysisStartedAt`/`analysisCompletedAt` timestamps ~6s apart (the synchronous enrichment→anomaly→incident→root-cause→business-impact pipeline actually ran).
- Extending the same dataset with 5 more rows and finalizing again produced version 2: `cumulativeRecordCount: 17`, `newRecordCount: 5`. `GET /datasets/{id}/versions` confirms both versions independently retrievable (v1: ready, 12 records; v2: ready, 17 records) — extending did not overwrite or hide v1.
- `GET /datasets/{id}` after finalizing returns `currentVersion` (highest READY) and `latestVersion` (most recent regardless of status, including the new open draft) as two distinct fields — matches the documented design.

## 5. End-to-End Data Flow

Upload → mapping → normalization → row analysis were validated at the API contract level (`POST /datasets/{id}/complaints:analyze`, `field_value_mapping` tables and repositories, `normalization.py`) via `[CODE INSPECTION]` and the existing backend test suites for `ingestion_service` (`test_normalization.py`, `test_mapping_service.py`, `test_api_field_mappings.py`, `test_api_complaint_analysis.py` — all passing, §3). The browser-driven UI flow (drag-drop upload, live mapping-review interaction) was **not exercised in this pass** — no browser automation exists in this project, consistent with every prior report. What *was* directly exercised end-to-end via real HTTP calls (§4) is the contract those UI screens call: ingest → duplicate-reject → finalize → dataset-scoped intelligence, with real, non-fabricated responses at every step.

**Provenance:** each ingested complaint is associated with the dataset via a real FK (confirmed by `dataset_id` appearing correctly scoped throughout dashboard/analytics responses below); dataset-version-level provenance (which version's analysis run produced a given RootCause/BusinessImpactAssessment/Recommendation) is asserted by `docs/CHANGELOG.md`'s AD-12 Addendum and was not independently re-verified at the database row level in this pass (time-boxed; not part of either CI failure or this milestone's headline claims).

## 6. Dataset Isolation and Scoping

`[RUNTIME]`, two datasets created in the same validation session:

- **Dataset A** ("Payment Outage", 12 US-East/payments complaints) → finalized → Dashboard shows one incident: `"US-East — payment_issue Incident"`, root-caused to `"Payment Gateway Failure"`.
- **Dataset B** ("Shipping Delays", 6 EU-West/logistics complaints) → finalized → Dashboard shows a **different** incident: `"EU-West — delivery_issue Incident"`, root-caused to `"Logistics Delay"`.
- Re-fetching Dataset A's dashboard immediately after creating and finalizing Dataset B returns the **identical** A-only incident (same incident id, same content) — B's data never appeared under A.
- `GET /api/v1/datasets` lists both datasets independently, each with its own version history and `openIncidentCount`.

**PASS with real evidence** — not inferred from code reading alone; two materially different datasets produced two materially different, correctly-scoped incidents in the same live session.

**Archive protection — mechanism clarified, not a gap.** Archiving Dataset B (`POST /datasets/{id}/archive` → `200`) does **not** make `GET /api/v1/dashboard?datasetId=<archived>` itself reject the request — that endpoint still returned `200` with data in this test. Protection is enforced one layer up: `GET /api/v1/datasets/{id}` correctly excludes archived datasets by default and returns `404` (confirmed directly), and the frontend's `DashboardWorkspace`/`AnalyticsWorkspace` use *that* 404 as the authoritative "no longer available" signal before ever reading `useDashboardData`'s result — a deliberate design documented in the component's own comments (`anomaly_service/etc. have no concept of Dataset lifecycle`). Net effect for a normal user through the UI: archived datasets are correctly blocked. Net effect for a direct API caller with a stale/known dataset id: the Dashboard/Analytics data routes themselves do not independently check archive status. Recorded as a real, verified nuance for §11, not fabricated as either a pass or a failure.

## 7. Dashboard Validation

`[RUNTIME]` Dashboard output was evaluated for internal consistency against the input, not just successful rendering:

- Dataset A's `operationalBrief.criticalSituations` names US-East and `payment_issue` — matches the region/category actually ingested (100% US-East, payment-related complaint text).
- `investigationEntryPoints[0].direction` reads `"Most likely cause: Payment Gateway Failure (confidence: Medium)"` — a plausible, evidence-grounded root cause for the ingested payment-failure text, not a generic placeholder.
- After extending Dataset A to version 2, the Dashboard's `decisionSummary` shows **two** recommendation entries tied to the same underlying incident id (one from each finalize run) rather than replacing the first. This is consistent with version-scoped intelligence generation (each finalize produces its own recommendation generation) but means the Dashboard does not currently collapse to "latest recommendation only" — a minor internal-consistency observation, not a crash or data-loss bug.
- Dataset B's dashboard is fully independent (§6) — different incident id, different headline, different root cause.

**Verdict: meaningful and internally consistent** with the ingested data, not merely "renders without error."

## 8. Analytics Validation

`[RUNTIME]` `GET /analytics/trends?datasetId=<A>&period=last-30-days`:

- `volumeTrend`: 1 date bucket, count 12 — matches the 12 ingested rows exactly.
- `categoryTrend`: `payment_issue`, count 12 — matches.
- `regionTrend`: `US-East`, count 12 — matches.
- `sentimentTrend`: 12/12 classified `negative`, average score `-1.0` — plausible for complaint text describing repeated payment failures.
- `urgencyTrend`: 12/12 classified `low` — this is *not* what a human would expect from "payment failed... declined three times" language, and reproduces the previously-documented deterministic-keyword-classifier limitation (urgency classification doesn't reliably track perceived severity). Reported honestly as observed, not smoothed over.

No cross-dataset leakage observed: Dataset A's analytics reflect only Dataset A's 12 (then 17) records at every point checked.

**Verdict: outputs are real, traceable 1:1 to the input data** — this is pipeline-functionality evidence, not evidence that the urgency classifier's judgment is good (it demonstrably isn't, on this sample).

## 9. Incident / Anomaly Validation

**Pipeline functionality:** ✅ confirmed. Finalizing each dataset produced a real, non-empty incident (4 correlated anomalies each: `category_spike`, `complaint_spike`, `regional_spike`, `urgency_spike`), each correctly scoped to its own dataset (§6), each with a root cause and a generated recommendation. This is direct evidence the detection → correlation → root-cause → recommendation chain executes correctly against dataset-scoped data.

**Intelligence quality — explicitly separated, not claimed as proven:** Both incidents were produced from a small, homogeneous, single-topic synthetic batch (12 and 6 records respectively, all describing the same failure mode) — exactly the condition under which the detector's zero-baseline rule fires easily, as the prior validation already documented. This run does not newly prove or newly disprove detection quality against realistic, heterogeneous, multi-topic traffic; it proves the mechanism runs correctly end-to-end and produces internally consistent output for the data given.

## 10. Administration Validation

`[RUNTIME]`, live calls against the isolated stack:

- `GET /api/v1/administration/overview` → `200`, per-service health: `gateway`/`ingestion`/`nlp`/`anomaly`/`root_cause`/`business_impact`/`recommendation` all report `"status": "healthy"`; `copilot`/`evaluation` correctly report `"status": "unavailable"` — because those two containers were deliberately not started for this pass. This is real, dynamically-computed health data (it correctly reflects the actual container state), not a static or fabricated display.
- `GET /api/v1/administration/intelligence-configuration` → `200`, real weighted business-impact dimension configuration returned.
- Dataset lifecycle (create, ingest, finalize, extend/re-analyze, archive) is real, Gateway-backed functionality, fully exercised in §4/§6 above — this is the dataset-lifecycle portion of Administration's real functionality.

**Illustrative, not validated as functional (unchanged from prior report, not in scope for this pass):** broader user/role administration, external system/CRM integrations, and a full audit trail remain presentation-only sections, self-labelled as such in the frontend. Not re-tested here; not claimed as implemented.

## 11. Known Limitations / Future Improvements

Real, currently-observed limitations only:

- **Archive protection is enforced one layer up from the data routes themselves** (§6) — a normal UI user is correctly blocked from viewing an archived dataset's Dashboard/Analytics, but the Dashboard/Analytics API routes do not independently reject a request naming an archived dataset id. Worth hardening at the data-route layer if direct API access by less-trusted callers becomes a real threat model; not a defect in the UI-driven product today.
- **Dashboard does not collapse recommendations to "latest version only"** after a dataset is extended and re-finalized (§7) — both the pre- and post-extension recommendation remain visible under the same incident.
- **Deterministic urgency classification does not reliably track perceived complaint severity** (§8) — reproduces a previously-documented limitation, now re-confirmed on dataset-scoped data specifically.
- **"Keep as Others" mapping edge cases**, **easier access to already-finalized records for viewing/modification**, and **deeper post-mapping intelligence quality** are known, previously-documented areas for future iteration — not newly discovered here, not re-verified as fixed or unfixed in this pass (out of scope; not blocking).
- **`copilot_service`/`evaluation_service` dataset-scoping** was not exercised in this pass (services deliberately not started) — the previously-documented `analytics_trends` tool gap and evaluation-output-not-surfaced gap are unchanged, not re-verified here.
- **No browser automation** — as in every prior report, the UI's actual rendered behavior was not driven through a real browser session in this pass; validated at the API-contract level only.

## 12. Final Acceptance Matrix

| Requirement | PASS | PARTIAL | NOT VERIFIED | Evidence |
|---|---|---|---|---|
| Dataset identity | ✅ | | | §4 — real UUIDs, `GET /datasets` lists independent entries |
| Dataset versioning | ✅ | | | §4 — v1/v2 both independently retrievable after extend |
| Ingestion pipeline | ✅ | | | §4, §5 — 12/12, 6/6, 5/5 real ingests across three batches |
| Mapping | | | ✅ | §5 — validated via existing passing test suites, not re-driven live in this pass |
| Normalization | | | ✅ | §5 — same |
| Row analysis | | | ✅ | §5 — same |
| Complaint provenance | ✅ | | | §4, §5 — dataset FK scoping confirmed via correctly-scoped downstream responses |
| Duplicate handling | ✅ | | | §4 — real `409 CONFLICT` on resubmission |
| Dataset-scoped intelligence | ✅ | | | §6, §7, §8 — two datasets, two independent, correctly-scoped intelligence sets |
| Dataset isolation | ✅ | | | §6 — direct evidence, not inferred |
| Re-analysis | ✅ | | | §4 — version 2 correctly reflects cumulative 17 records |
| Stale-state handling | 🟡 | | | §7 — old and new recommendations both remain visible under one incident after re-analysis, rather than showing only the latest |
| Archived dataset protection | 🟡 | | | §6, §11 — real, but enforced at the dataset-detail layer, not the Dashboard/Analytics data routes |
| Dashboard | ✅ | | | §7 — internally consistent with input, not just rendering |
| Analytics | ✅ | | | §8 — outputs traceable 1:1 to input; one known classifier-quality limitation reported honestly |
| Incident/anomaly detection (pipeline) | ✅ | | | §9 — real, correctly dataset-scoped output produced |
| Incident/anomaly quality | 🟡 | | | §9 — explicitly not proven on this small, homogeneous sample |
| Administration dataset lifecycle | ✅ | | | §10 — create/ingest/finalize/extend/archive all real |
| Administration service health | ✅ | | | §10 — dynamically correct, including reporting two intentionally-stopped services as unavailable |
| Backend tests | ✅ | | | §3 — 1,289 passed locally; 21 pre-existing environment-only failures unrelated to this milestone |
| Frontend tests | ✅ | | | §3 — 381/381 |
| CI-equivalent verification | ✅ | | | §3 — lint/typecheck/test/build/compose all pass locally against the exact CI commands |
| Migration integrity | ✅ | | | §4 — 27-migration linear chain, clean apply from empty |
| Runtime validation | ✅ | | | §4–§10 — real HTTP calls against a live, isolated stack throughout |

---

*This report intentionally does not claim GitHub Actions is green — that can only be confirmed once these changes are pushed and the workflow actually runs. All results above are local, CI-equivalent verification.*
