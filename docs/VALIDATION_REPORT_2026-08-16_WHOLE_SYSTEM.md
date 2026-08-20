> **Historical record, preserved verbatim.** This is the original whole-system validation report (F05/F06, Phase 13 closure), exactly as committed on 2026-08-16 (commit `2db4f43`) before `docs/VALIDATION_REPORT.md` was rewritten on 2026-08-20 to cover the newer dataset/dataset-version and ingestion-stabilization milestone. It is retained here, unedited, because several documents (`docs/PROJECT_STATUS.md`) cite specific sections of it (e.g. §9's RC1–RC4 addendum) and because it remains real, valid evidence for everything it covers — Copilot, `evaluation_service`, observability, and backup/restore were not re-validated in the 2026-08-20 pass, so this document is still the current evidence for those areas. For the current, actively-maintained validation record, see [`docs/VALIDATION_REPORT.md`](VALIDATION_REPORT.md).

---

# Final Synthetic-Data Validation Report (F05/F06)

**Validation date:** 2026-08-16
**Scope:** Phase 13 closure items F05 (end-to-end synthetic-data validation) and F06 (whole-project completion validation).
**Outcome:** 🟡 **Complete with documented limitations** — the full intelligence pipeline, authentication/RBAC, attribution, Copilot ownership, observability, and backup/restore were all exercised against real running services and passed. Remaining gaps are pre-existing, already-documented prototype limitations.

Every claim below is labelled by evidence type:

| Label | Meaning |
|---|---|
| `[RUNTIME]` | Executed during this validation against real running services; output observed directly. |
| `[TEST]` | Produced by an automated test suite run during this validation. |
| `[CODE INSPECTION]` | Read from source; not executed during this validation. |
| `[DOCUMENTATION]` | Claimed by a project document; not independently re-verified here. |

---

## 1. Environment

| Item | Value |
|---|---|
| Host | Windows 11, Docker 29.2.1, Docker Compose v5.1.0 |
| Host Python (test runner) | 3.13.0 (containers and CI use 3.11) |
| Dev stack | Compose project `customer_experience_intelligence_and_failure_detection_platform` (`oi_*` containers), persistent `postgres_data` volume |
| Validation stack | Compose project `oival` — a **separate, disposable stack on its own empty volume**, created so F05 could run against a genuinely fresh database without touching the persistent dev database |
| Services started | `postgres` + all 9 backend services (gateway, ingestion, nlp, anomaly, root_cause, business_impact, recommendation, copilot, evaluation) |
| Not started | Frontend container, Prometheus/Grafana/Loki/Promtail/Tempo/otel-collector (outside the harness's required set) |
| External LLM provider | **Not configured.** `.env.example` ships `LLM_PROVIDER=none` with empty `LLM_API_KEY`; the local `.env` sets no LLM variables at all. All Copilot verification below exercises the honest `NullLLMProvider` fallback. |

`[RUNTIME]` Both Compose files validate cleanly:
`docker compose config --quiet` → exit 0; `docker compose -f docker-compose.prod.yml config --quiet` → exit 0.

`[RUNTIME]` All 10 containers reached `healthy`. All 9 services returned `200 {"status":"ready","checks":{"database":"ok"}}` from `/health/ready`.

---

## 2. Dataset & Scenarios

The harness is `datasets/validation/run_validation.py`. It has **no CLI arguments**; it is designed to be `docker cp`'d into a running container and executed from inside the Docker network, because only `gateway_service` and `postgres` are host-published. It generates its data in-process (it does **not** read `datasets/sample_complaints/operational_seed.json`, which is a separate 8-record seed file used for manual seeding).

`[CODE INSPECTION]` Two scenario populations, 24 complaints total:

| Scenario | Records | Design |
|---|---|---|
| **A — Baseline (negative control)** | 10 | Spread across 5 regions × 5 neutral texts, 6–37 days ago. Intended to be unremarkable. |
| **B–F — Concentrated spike** | 14 | Single region (US-West), delivery-failure language, highly-negative/critical urgency, all within the last ~2 days. One incident intended to satisfy the spike (B), regional-anomaly (C), customer-impact (D), root-cause-pattern (E) and recommendation (F) purposes simultaneously. |

The harness's own docstring documents this consolidation honestly — six requested scenario *purposes* are covered by two real complaint populations, not six manufactured incidents.

---

## 3. F05 — Synthetic-Data Validation

### 3.1 Execution

`[RUNTIME]` **First run — against the persistent dev database: inconclusive.**
All 24 ingestion calls returned `409 "A complaint with this signature already exists."` because prior runs of the same deterministic harness had left `VALIDATION-*` records in the dev database (76 such rows present). NLP enrichment was therefore skipped for every record, `/anomalies/run` detected nothing new, and root-cause returned `409 RootCause already exists`. This run is **not** valid pipeline evidence — it only demonstrates that source-hash deduplication works. It is recorded here rather than discarded.

`[RUNTIME]` **Second run — against a fresh, isolated database: valid.**
A separate Compose project (`oival`) was started on its own empty volume. `python -m alembic upgrade head` applied all 17 migrations from empty to head `e35a123597e1` with **exit code 0** — independently re-confirming the AD-7 fresh-database migration fix. The harness then ran to completion:

```
docker cp datasets/validation/run_validation.py oival_gateway:/tmp/run_validation.py
docker compose -p oival exec -T gateway_service python /tmp/run_validation.py
→ exit code 0, all 13 stages executed
```

### 3.2 Scenario Results

| Scenario | Result | Evidence | Notes |
|---|---|---|---|
| **A — Baseline (negative control)** | ⚠️ PASS WITH LIMITATION | `[RUNTIME]` 10/10 ingested (`201`), 10/10 enriched (`201`), correct neutral/low labels | The baseline **did** trigger CRITICAL anomalies. Against an empty database every dimension has a zero baseline, so the detector's `undefined_baseline (zero baseline with new activity) -> CRITICAL` rule fires for all 5 baseline categories and their regions. The negative control does not hold on a cold-start database. See §6. |
| **B — Complaint spike** | ✅ PASS | `[RUNTIME]` `complaint_spike:global:ALL`, baseline=2, current=22, `+1000.0%`, severity `critical`, rule `percentage_change magnitude 1000.0% > 200% -> CRITICAL` | Correct arithmetic; 2 baseline records fall outside the 30-day current window. |
| **C — Regional anomaly** | ✅ PASS | `[RUNTIME]` `regional_spike:region:US-West`, current=16, severity `critical` | US-West correctly isolated as the highest-volume region. |
| **D — Customer/business impact** | ✅ PASS | `[RUNTIME]` Assessment `39a46974…`: financial `critical`, customer `medium`, operational `critical`, SLA `none`, reputation `none`, overall score 62 / `high`, confidence 60, 22 affected customers, full explanation string | Structurally valid and fully explained. Reputation scored `none` — see §6. |
| **E — Root-cause pattern** | ✅ PASS | `[RUNTIME]` Root cause `6c1836dd…`: `service_outage`, confidence 100 (`Very High`), 4 weighted evidence entries (category 40, severity 25, urgency 20, region 15) | Deterministic and explainable. |
| **F — Recommendation generation** | ✅ PASS | `[RUNTIME]` 3 recommendations from one generation `d7204bdd…`: `escalate`/critical/80, `mitigate`/high/80, `infrastructure_action`/high/67 — each with rationale, priority rationale and cited supporting evidence | Produced automatically via the real async `BusinessImpactCompleted` fan-out, not a direct call. |

### 3.3 Pipeline Layer Validation

| Layer | Result | Evidence |
|---|---|---|
| Ingestion | ✅ PASS | `[RUNTIME]` 24/24 `201 Created`; re-run produced 24/24 `409` (deduplication works) |
| Persistence | ✅ PASS | `[RUNTIME]` 24 complaints, 24 enrichments, 12 anomalies, 1 incident, 12 incident_anomalies, 1 root cause, 1 assessment, 3 recommendations, 1 generation, 1 evaluation |
| NLP enrichment | ✅ PASS | `[RUNTIME]` 24/24 `201`; sentiment/urgency/category/keywords/summary plus `explainability_metadata` with matched keywords and method for every record |
| Anomaly detection | ✅ PASS | `[RUNTIME]` 12 anomalies across 4 detector types (complaint/category/regional/urgency spike), each with fingerprint, baseline, current, triggered rule and explanation |
| Incident correlation | ⚠️ PASS WITH LIMITATION | `[RUNTIME]` 1 incident `INC-91F462E2`, "Multi-Signal Incident (12 anomalies)", severity `critical`, confidence 55 (`Possible`) | All 12 anomalies — baseline and spike alike — were merged into a single incident rather than isolating the US-West delivery incident. See §6. |
| Root cause | ✅ PASS | `[RUNTIME]` `201 Created`, deterministic, evidence-weighted |
| Business impact | ✅ PASS | `[RUNTIME]` `201 Created`, 5-dimension weighted score with explanation |
| Event fan-out | ✅ PASS | `[RUNTIME]` `BusinessImpactCompleted` produced both a recommendation generation **and** an evaluation with no direct call to either service |
| Recommendation | ✅ PASS | `[RUNTIME]` `200`, 3 prioritized recommendations with cited evidence |
| Evaluation | ✅ PASS | `[RUNTIME]` `200`, evaluation `60991856…`: valid, quality 80 (`high`), explainability 100 (`high`), confidence summary 100/60/80.0 |
| API / Gateway | ✅ PASS | `[RUNTIME]` Dashboard, analytics, investigation, administration and recommendation routes all served real aggregated data (§5) |
| Copilot | ⚠️ PASS WITH LIMITATION | `[RUNTIME]` Fully functional except that no LLM is configured (§7) |

### 3.4 Data Quality

`[RUNTIME]` Queried directly against the fresh database:

- Expected record counts exactly met (24 complaints → 24 enrichments; 1:1, no gaps).
- **Zero duplicate** `external_reference_id` values.
- **Zero nulls** in `complaint_text`, `event_occurred_at`, `customer_region`.
- All 12 anomalies linked to the incident via `incident_anomalies` (12 rows) — no orphans.
- Sentiment/urgency/category enums all structurally valid; timestamps all timezone-aware.
- Anomaly records carry complete `baseline_value` / `current_value` / `triggered_rule` / `explanation`; recommendations carry non-empty `action`, `recommendationRationale`, `priorityRationale` and `supportingEvidence`.

Nullable-by-design fields (`percentage_change` on zero-baseline anomalies, `entity_value` on global anomalies, `resolved_at` on an open incident) are correctly null and are **not** counted as defects.

### 3.5 Intelligence Output

`[RUNTIME]` Structural correctness confirmed across all stages. Two honest observations about scenario *intent* (not structural defects):

1. **The negative control does not hold on a cold-start database.** All 5 baseline categories and 3 regions produced CRITICAL anomalies via the zero-baseline rule. On a database with history the rule would not fire; on an empty one it fires for everything. The harness's stated expectation that the baseline "must NOT itself produce a strong anomaly" was **not met**.
2. **NLP urgency classification within the spike cohort is mixed.** Of the 14 spike complaints — all written with deliberately critical language — 9 were labelled `CRITICAL`, 2 `HIGH`, and 5 `LOW`. The deterministic keyword classifier behaves as designed (`[CODE INSPECTION]`) but does not uniformly reflect the cohort's intent. This is an inherent property of ARCH-004 (deterministic NLP for MVP), not a regression.

### 3.6 Recommendation Validation

| Check | Result | Evidence |
|---|---|---|
| Recommendations persisted | ✅ PASS | `[RUNTIME]` 3 rows under one `generation_id` |
| Decision flow works | ✅ PASS | `[RUNTIME]` `PATCH /recommendations/{id}/decision` → `200`, `decision=APPROVED`, `decisionNote`, `decidedAt` |
| `decided_by` from trusted auth | ✅ PASS | `[RUNTIME]` `decided_by = 950e79c0-…` = `operator@validation.local`, the authenticated session's own identity |
| **Spoofing rejected** | ✅ PASS | `[RUNTIME]` A `PATCH` body containing `"decided_by": "00000000-0000-0000-0000-000000000000"` returned `200` and stored the **real operator's** id — the client-supplied value was discarded, never honoured |
| History row created | ✅ PASS | `[RUNTIME]` 2 rows in `recommendation_decision_history`, each with `actor_id` correctly resolving to `operator@validation.local` |

### 3.7 Copilot Validation

> **External LLM provider: NOT CONFIGURED.** `LLM_PROVIDER` is unset in this environment and no `LLM_API_KEY` exists anywhere in the repository. Nothing below demonstrates real language-model reasoning.

| Check | Result | Evidence |
|---|---|---|
| Endpoint availability | ✅ PASS | `[RUNTIME]` `POST /api/v1/copilot/messages` → `200` |
| Requires authentication | ✅ PASS | `[RUNTIME]` Anonymous → `401` |
| Requires `operator` role | ✅ PASS | `[RUNTIME]` Authenticated `viewer` → `403` |
| Conversation persistence | ✅ PASS | `[RUNTIME]` Conversation row with `owner_id` = the authenticated operator; 4 ordered `copilot_messages` rows (USER/ASSISTANT × 2 turns) |
| Two-turn continuity | ✅ PASS | `[RUNTIME]` Second turn against the same `conversationId` → `200`, appended to the same conversation |
| Workspace context persisted | ✅ PASS | `[RUNTIME]` `workspaceContext` persisted `workspace=investigations`, `incident_id=e09d6777-…` |
| Ownership isolation | ✅ PASS | `[RUNTIME]` Operator B on operator A's conversation → `403 "You do not have access to this conversation."`; delete → `403`; A's own delete → `204` |
| **Honest no-LLM fallback** | ✅ PASS | `[RUNTIME]` `"answer": "Copilot's language model is not configured in this environment, so this request cannot be interpreted."`, `limitations: ["No LLM provider is configured (LLM_PROVIDER is unset); no tool was called."]` — no fabricated answer, no invented evidence |

### 3.8 F05 Final Result

**PASS WITH LIMITATIONS.** All 13 harness stages executed successfully end-to-end on a fresh database (exit code 0). Every pipeline layer produced real, structurally valid, explainable output. The three limitations are: the cold-start negative control, single-incident correlation of all anomalies, and the absence of a real LLM behind Copilot.

---

## 4. F06 — Whole-Project Completion Validation

### 4.1 Backend Services

| Service | State | Evidence |
|---|---|---|
| `gateway_service` | ✅ COMPLETE | `[RUNTIME]` healthy, 12 routes, auth + RBAC enforced, aggregation verified. `[TEST]` 20 test files |
| `ingestion_service` | ⚠️ PARTIAL | `[RUNTIME]` healthy, ingestion + dedup verified. **No dedicated test suite** (0 test files) — matches the documented limitation |
| `nlp_service` | ✅ COMPLETE | `[RUNTIME]` 24/24 enrichments with explainability metadata. `[TEST]` 7 test files |
| `anomaly_service` | ✅ COMPLETE | `[RUNTIME]` 12 anomalies + incident correlation. `[TEST]` 26 test files |
| `root_cause_service` | ⚠️ PARTIAL | `[RUNTIME]` analysis verified. Confirm/reject/refresh exists at service level but is **not Gateway-exposed** — matches documentation. `[TEST]` 17 test files |
| `business_impact_service` | ✅ COMPLETE | `[RUNTIME]` assessment + event publication verified. `[TEST]` 25 test files |
| `recommendation_service` | ✅ COMPLETE | `[RUNTIME]` generation, decision, attribution, history verified. `[TEST]` 26 test files |
| `copilot_service` | ⚠️ PARTIAL | `[RUNTIME]` orchestration, persistence, ownership all real; **no LLM configured**. `[TEST]` 19 test files |
| `evaluation_service` | ⚠️ PARTIAL | `[RUNTIME]` computes and persists real evaluations; **no Gateway route surfaces them**. `[TEST]` 17 test files |

### 4.2 Authentication & RBAC

`[RUNTIME]` 31/31 checks passed in a single clean run against the live Gateway:

- Anonymous → all 6 protected routes + decision PATCH + Copilot → `401`.
- Wrong password → `401` (`"Invalid email or password."`, no user enumeration).
- `viewer` → login `200`, `/auth/me` `200`, dashboard/analytics/investigation/administration `200`.
- `viewer` → decision PATCH `403`, Copilot `403` (401-before-403 ordering correct).
- `operator` → decision PATCH `200`, Copilot `200`.
- Logout `204`, then `/auth/me` `401` (session genuinely invalidated).
- Session cookie: `HttpOnly`, `SameSite=lax`, `Max-Age=1800`, `Path=/`. **No `Secure` flag** in the development configuration.
- Login response body contains only `userId`/`email`/`roles` — no token, no hash.

`[RUNTIME]` The bootstrap tool (`AD-8`) was verified in all three states: creates the admin, is idempotent on re-run (`"no password change performed"`), and fails clearly when credentials are absent (`"BOOTSTRAP_ADMIN_EMAIL is not configured."`).

### 4.3 Observability

| Check | Result | Evidence |
|---|---|---|
| Prometheus metrics | ✅ PASS | `[RUNTIME]` `/metrics` → `200`, 36 KB; `http_requests_total` correctly labelled by method/route/status/service |
| No high-cardinality labels | ✅ PASS | `[RUNTIME]` Routes appear as templates (`/api/v1/recommendations/{recommendation_id}/decision`), never with real UUIDs |
| Structured JSON logs | ✅ PASS | `[RUNTIME]` Logs carry `timestamp`, `level`, `service`, `logger`, `message`, `request_id`, `status_code`, `error_code`, `route` |
| Correlation ID | ⚠️ PARTIAL | `[RUNTIME]` A client-supplied `X-Request-ID` is reused, echoed in the response header, and returned in the error envelope's `requestId`. It appears in Gateway structured logs. It was **not** observable in downstream services' logs — those log 404s via plain uvicorn access logging. `[CODE INSPECTION]` Forwarding is genuinely implemented (`correlation_headers()` used on every Gateway/Copilot/event-publisher outbound call) |
| **No secret leakage** | ✅ PASS | `[RUNTIME]` All 9 services' logs scanned: 0 plaintext passwords, 0 bcrypt hashes, 0 JWTs, 0 internal-secret values |

`[RUNTIME]` One narrow exception: the **operator-invoked bootstrap script** prints its `INSERT` statement — including the bcrypt hash — to stdout, because `backend/shared/database/database.py` sets `echo=(ENVIRONMENT == "development")`. This affects only that one script's console output in development (the hash, never the plaintext password), and no running service log. Minor, disclosed.

### 4.4 Backup & Restore

| Check | Result | Evidence |
|---|---|---|
| Migration head | ✅ PASS | `[RUNTIME]` `e35a123597e1`; 17 migrations, single linear chain, no branches |
| Backup creates a valid dump | ✅ PASS | `[RUNTIME]` `pg_dump -Fc` against the real dev database → `operational_intelligence_20260816T091423Z.dump`, 190,365 bytes. Read-only; the dev database was never modified |
| Restore safety guard active | ✅ PASS | `[RUNTIME]` `_guard_target_container` refuses both `oi_postgres` and `postgres`; allows only isolated names |
| Full isolated round-trip | ✅ PASS | `[TEST]` All 8 tests in `test_backup_restore.py` pass, including `test_real_backup_then_restore_verification_round_trip`, which restores into a throwaway container and tears it down. **The real dev database was never a restore target.** |

### 4.5 Docker & Infrastructure

`[RUNTIME]` Dev and prod Compose both validate (`config --quiet` → exit 0). `[CODE INSPECTION]` The prod configuration removes bind mounts and `--reload`, un-publishes PostgreSQL, segments the network, and runs non-root; every service has a healthcheck and `restart: unless-stopped`.

⚠️ **Reproducibility gap:** the repository's local `.env` is missing several keys present in `.env.example` (`INTERNAL_SERVICE_SECRET`, `LLM_PROVIDER`, `TRACING_ENABLED`, `OTLP_EXPORTER_ENDPOINT`, `PROMETHEUS_PORT`, `GRAFANA_PORT`, `BOOTSTRAP_ADMIN_*`). `[CODE INSPECTION]` Every one of them has a matching code-level default, so nothing breaks — but a fresh clone should copy `.env.example`, and the bootstrap variables must be set explicitly by the operator. `.env` is correctly gitignored and untracked.

### 4.6 CI

`[CODE INSPECTION]` `.github/workflows/ci.yml` runs three jobs whose commands were verified to match the current repository:

- `pytest backend -q` after `alembic upgrade head` — matches `[TEST]` local behaviour. All 9 `requirements.txt` files plus `backend/requirements-test.txt` exist at the referenced paths.
- `npm run lint` / `typecheck` / `test` / `build` — all four scripts exist in `frontend/package.json` and all four pass locally `[TEST]`.
- `docker compose config` for both files — both pass locally `[RUNTIME]`.

⚠️ At the time of this validation the workflow still carried a long "KNOWN ISSUE" comment describing the `f05ea2afc3ee` enum-creation migration bug as unfixed. `[RUNTIME]` That bug is **fixed** — migrations now apply cleanly from empty. The comment was stale documentation inside a working file; it has since been corrected during the final release-readiness pass (comment text only — no job, step, or dependency was changed).

### 4.7 Security

| Check | Result | Evidence |
|---|---|---|
| No committed secrets | ✅ PASS | `[RUNTIME]` Scanned all tracked files for API-key/private-key/token patterns — none found. `.env` untracked; `/backups/` gitignored |
| Actor identity server-derived | ✅ PASS | `[RUNTIME]` Spoofed `decided_by` discarded; Copilot `owner_id` taken from the session |
| Auth bypass | ✅ PASS | `[RUNTIME]` No unauthenticated access to any protected route; internal mutation routes are not Gateway-exposed and require `X-Internal-Secret` (`[CODE INSPECTION]`: constant-time compare, fails closed, never distinguishes missing from wrong) |
| Cookie flags | ⚠️ PARTIAL | `[RUNTIME]` `HttpOnly` + `SameSite=Lax` present; **no `Secure` flag** — acceptable for local HTTP development, would need setting behind TLS |
| Credential leakage in logs | ✅ PASS | `[RUNTIME]` See §4.3 |

### 4.8 Frontend

`[TEST]` Lint, typecheck and production build all pass. The suite is 337 tests / 48 files, of which 336 passed in the full run — the single failure was a load-sensitive timing flake that passes standalone (see §5).

`[CODE INSPECTION]` Route protection (`RequireAuth`), auth flow, five workspaces, and the Copilot panel all exist and are tested. The three specifically documented limitations were each re-checked and remain **accurately documented** — none has become an undisclosed gap:

- **Role-aware UX** — 🟡 still a KNOWN LIMITATION. `roles` is present on the auth type but is used nowhere to gate UI controls.
- **Administration placeholders** — 🟡 still a KNOWN LIMITATION. Four of six sections remain presentation-only, self-labelled in code.
- **Root-cause decision actions** — 🟡 still a KNOWN LIMITATION. No Gateway route exposes confirm/reject/refresh.

> **Not verified:** no browser automation was run. All frontend evidence is from the test suite and source inspection, never from a real rendered browser session.

---

## 5. Test Results

| Suite | Result | Notes |
|---|---|---|
| Backend `pytest backend -q` | ✅ **1,376 passed, 0 failed** | 330 s. One initial failure (`test_real_backup_then_restore_verification_round_trip`) was caused by *this validation's own* isolated stack occupying port 55432; with the port free it passes. Re-confirmed: 8/8 backup/restore tests pass |
| Frontend `npm test` | ✅ **337 tests / 48 files**, 336 passed | One failure (`AppRouter.test.tsx`, 5 s timeout) under concurrent load; **passes standalone** in 15 s. A load-sensitive timing flake, not a product defect |
| Frontend `npm run lint` | ✅ PASS | Clean |
| Frontend `npm run typecheck` | ✅ PASS | Clean |
| Frontend `npm run build` | ✅ PASS | Built in 2.34 s |
| Validation harness | ✅ PASS | Exit code 0, 13/13 stages |

**New failures vs. pre-existing:** no new failures. Both observed failures were environmental artefacts of this validation run and both resolve on re-run in isolation. The two issues `docs/PROJECT_STATUS.md` carried forward from Phase 12 (`business_impact_service`'s missing `httpx`, and the migration enum bug) are **both now fixed** — `httpx==0.27.0` is declared, and migrations apply cleanly from empty.

---

## 6. Limitations & Findings

### 🟡 Known limitations — confirmed still accurate

1. **No external LLM provider.** Copilot's orchestration, tool boundary, persistence and ownership are real and tested; its reasoning has never been exercised against a live model.
2. **Role-aware frontend UX** does not exist; backend RBAC is authoritative.
3. **Administration workspace**: 2 of 6 sections show real data.
4. **Root-cause confirm/reject/refresh** is service-level only, not Gateway-exposed.
5. **`evaluation_service` output** is computed and persisted but surfaced nowhere.
6. **`ingestion_service`** has no dedicated test suite.

### 🟡 Newly documented by this validation

7. **Cold-start anomaly sensitivity.** On an empty database every dimension has a zero baseline, so the `undefined_baseline -> CRITICAL` rule fires for essentially all activity — including the deliberate negative control. The detector behaves as specified; the *validation scenario's* negative-control assumption does not hold on a fresh database.
8. **Coarse incident correlation.** All 12 anomalies — baseline and spike alike — correlated into one "Multi-Signal Incident" purely on a 15-minute time window and shared severity. The intended US-West delivery incident was not isolated as its own incident.
9. **Business impact ignores NLP sentiment.** The assessment scored reputation `none` with the reason *"No negative sentiment signal detected"*, despite 12 of 24 complaints being classified `HIGHLY_NEGATIVE`/`NEGATIVE` by `nlp_service`. Business impact consumes anomaly/trend metrics only; no sentiment-spike anomaly type exists to carry that signal through. Internally consistent, but enriched sentiment does not currently influence business impact.
10. **`estimated_affected_customers` counts the whole window** (22), not the incident's own complaints (14).
11. **SQLAlchemy `echo` in development** prints bound parameters, so the operator-run bootstrap script emits a bcrypt hash to its console.
12. **No `Secure` cookie flag** in the development configuration.
13. ~~**Stale CI comment** describing the already-fixed migration bug as unfixed.~~ **Resolved** during the final release-readiness pass — the comment now describes the fix (comment text only; CI behaviour unchanged).
14. **`.env` is missing keys** present in `.env.example`; all have safe code defaults.

### 🔴 Undocumented gaps

**None found.** Every previously documented limitation was re-verified as still accurate — none had silently worsened, and none was found to be concealing a defect.

### Transient, unreproduced

During one composite auth run, two checks that normally return `403` returned `401` instead. This did **not** reproduce across a subsequent full 31/31 run nor across 6 focused iterations. Recorded as an unexplained one-off, not a confirmed defect.

---

## 7. Final Completion Decision

## 🟡 PROJECT COMPLETE WITH DOCUMENTED LIMITATIONS

1. `[RUNTIME]` The complete intelligence pipeline works end-to-end on a fresh database — ingestion → NLP → anomaly → incident → root cause → business impact → evaluation → recommendation, including the real asynchronous event fan-out.
2. `[RUNTIME]` Authentication, RBAC, and attribution are genuinely enforced: 31/31 checks passed, and a deliberate spoofing attempt was discarded in favour of the server-derived identity.
3. `[TEST]` 1,376 backend tests pass; of the 337 frontend tests, 336 passed in the full run and the one failure is a load-sensitive timing flake that passes standalone (§5). Lint, typecheck and production build are clean.
4. `[RUNTIME]` Setup is reproducible from a fresh clone: both Compose files validate, migrations apply cleanly from empty, and the bootstrap tool creates the first user correctly.
5. `[RUNTIME]` Backup/restore is real and safe — the restore guard actively refuses the production database name.
6. `[RUNTIME]` No secrets leak into logs or responses; no secrets are committed.
7. Documentation is honest: every one of the six documented limitations was re-verified as accurate, and **no undocumented gap was found**.
8. It remains an **engineering prototype** — no deployment, no live traffic, no external LLM.
9. The limitations added by this validation (§6) are genuine intelligence-quality observations, not blockers.

---

## 8. Recommended Optional Improvements

None of these block completion:

- Give the anomaly detector a minimum-volume floor so a zero baseline cannot alone produce CRITICAL.
- Correlate incidents by shared entity (region/category) in addition to time window.
- Feed NLP sentiment into business-impact scoring, or add a sentiment-spike anomaly type.
- Scope `estimated_affected_customers` to the incident's own complaints.
- ~~Remove the stale "KNOWN ISSUE" comment from `.github/workflows/ci.yml`.~~ Done during the final release-readiness pass.
- Set `Secure` on the session cookie when served over TLS.
- Add a dedicated `ingestion_service` test suite.
- Have the validation harness namespace its `external_reference_id`s per run so it can be re-run against a non-empty database.

---

## 9. Addendum — 2026-08-16 Post-Closure Correction Pass (RC1–RC4)

### 9.1 Why this validation did not catch these defects

This report's coverage of the frontend was, in hindsight, structurally blind in one specific way, and it is worth stating plainly rather than quietly fixing.

Every HTTP check in §§3–6 was issued **directly against the Gateway** (`http://localhost:8000/api/v1/...`) using hand-written paths. The frontend was verified only by `[TEST]` (its own Vitest suite) and `[CODE INSPECTION]`. Nothing in this validation ever exercised the path strings the frontend's own API modules actually emit. Because those modules were missing the `/v1` segment, and because each frontend test asserted the same bare path its source module used, both layers agreed with each other and disagreed with the running Gateway — a defect class that is invisible to a suite that mocks `fetch` and a validation that bypasses the client.

The frontend container was also explicitly "not started" during F05 (§1). The first time anyone loaded the actual application in a browser, every workspace failed. That walkthrough — not this report — is what found it.

**Correction to the validation method, for any future pass:** at least one check per frontend workspace must go through the frontend's own API module or the frontend's served origin, not a hand-written Gateway URL.

### 9.2 What the correction pass validated

Against the running dev stack (`oi_*` containers, persistent `postgres_data` volume — not reset), authenticated with a bootstrap-created admin session cookie, through the frontend's own origin and proxy (`http://localhost:3000/api/...`):

| Check | Result |
|---|---|
| `POST /api/v1/auth/login` | `[RUNTIME]` `200` |
| `GET /api/v1/auth/me` | `[RUNTIME]` `200`, correct identity and roles |
| `GET /api/v1/dashboard?timeRange=7d` | `[RUNTIME]` `200`, 6,037 bytes |
| `GET /api/v1/analytics/trends?period=last-30-days` | `[RUNTIME]` `200`, 2,055 bytes |
| `GET /api/v1/administration/overview` | `[RUNTIME]` `200`, 741 bytes |
| `GET /api/v1/administration/intelligence-configuration` | `[RUNTIME]` `200`, 2,621 bytes |
| `GET /api/v1/investigations/{incident_id}` | `[RUNTIME]` `200`, 4,722 bytes |
| `GET /api/v1/recommendations/{recommendation_id}` | `[RUNTIME]` `200`, 799 bytes |
| Pre-fix bare paths (`/api/dashboard`, `/api/analytics/trends`, `/api/administration/overview`) | `[RUNTIME]` `404` — the defect itself, reproduced |
| Full frontend suite | `[TEST]` 339 passed, 49 files, 0 failed (`--maxWorkers=2`; the load-sensitive flakiness noted in §5 recurs at default concurrency) |
| `npm run lint` / `npm run typecheck` / `npm run build` | `[TEST]` all clean |
| Sample-data seed via `docker cp` + `--file` | `[RUNTIME]` 8 processed, 8 inserted, 0 duplicates, 0 errors |
| Sample-data seed with no `--file` | `[RUNTIME]` unchanged default resolution (`/app/datasets/sample_complaints/operational_seed.json`, absent by design) |

### 9.3 Not verified by this pass

- `[TEST]`-only, not browser-observed: that the sidebar renders exactly Dashboard/Analytics/Administration, and that an invalid URL renders `RouteErrorView` rather than react-router's raw error screen. Both are asserted by `src/tests/RouteErrorView.test.tsx` against the real route table and the real navigation config, but no browser walkthrough was performed. The owner's manual pass is what would confirm the rendered appearance.
- No visual/CSS verification of `RouteErrorView` in either theme.
