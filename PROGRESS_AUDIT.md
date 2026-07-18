# Progress Audit — Customer Experience Intelligence & Failure Detection Platform

Audit date: 2026-07-18
Method: Static, read-only inspection of the working tree against PROJECT_BRAIN.md, ARCHITECTURE.md, ROADMAP.md, REPOSITORY_STRUCTURE.md, PRD.md, CORE_ENTITY_SPECIFICATIONS.md, DATABASE_SCHEMA_ARCHITECTURE.md, ENTITY_MODELING_AND_OWNERSHIP.md, SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md, DATASET_AND_INGESTION_STRATEGY.md, MVP_DATASET_SCOPE.md. No files were installed, run, or modified; no dependencies were installed.

---

## 1. Git State

**There is no git repository.** `git status` fails with `fatal: not a git repository`, and no `.git` directory exists anywhere in the tree (confirmed by recursive search). There is a `.gitignore` file, but the repository was apparently never initialized (or the `.git` folder was removed/excluded from this copy).

Consequences:
- No branch, no remote, no commit count, no commit history to inspect.
- **No AI-attribution audit is possible** (no `Co-Authored-By` lines to search) because there is no commit log at all. Note: this is a materially different finding than "no AI attribution found" — there is simply no version history of any kind. If this is unexpected, the user should check whether a `.git` folder was stripped before this copy was made, or whether `git init` + first commit never happened.
- All engineering "progress" below is inferred purely from the current state of files on disk, with no way to see how or when they were introduced.

---

## 2. Roadmap Phase Status (13 phases, ROADMAP.md §3)

| # | Phase | Status | Evidence |
|---|-------|--------|----------|
| 1 | Foundation Setup | **Complete** | `docker-compose.yml` wires postgres + 8 services + frontend; `backend/shared/{config,database,logging,constants}` populated; `.env`/`.env.example` present and identical; Vite+React+TS frontend scaffolded and buildable in principle. |
| 2 | Operational Data Modeling | **Not started** | No `operational_events` model/table anywhere; `backend/tooling/dataset_generators/` contains only a `.gitkeep`; no synthetic event generator code exists; no complaint↔event mapping logic. |
| 3 | Data Ingestion Layer | **Partial** | `ingestion_service` has real `POST/GET /complaints` endpoints, a repository, hash-based dedup, and a seed loader (`backend/tooling/seed_data/load_sample_complaints.py`). But it only ingests **8 hand-written sample records** (`datasets/sample_complaints/operational_seed.json`) — no CFPB dataset loader, no CSV/bulk ingestion, no operational-event ingestion, no `ingestion_jobs` table. |
| 4 | NLP Intelligence Layer | **Partial** | `nlp_service` has a genuinely working enrichment pipeline (`enrichment_service.py`, `classifiers.py`) — real code, not a stub — but it is **keyword/regex-based deterministic classification**, not the ML/NLP models ARCHITECTURE.md calls for. One real test file exists (`test_api_enrichments.py`, uses mocks, well-written). |
| 5 | Trend & Anomaly Detection | **Not started** | `anomaly_service` is a bare FastAPI app with only a `/health` route. Zero files beyond `main.py`/`__init__.py` in any subfolder (api, core, models, repositories, schemas, services, utils all empty). |
| 6 | Root Cause Correlation | **Not started** | `root_cause_service` is identical bare `/health`-only stub. No `complaint_event_links` table/migration exists. |
| 7 | Business Impact Engine | **Not started** | `business_impact_service` is a bare `/health`-only stub. No `business_impacts` table/migration. |
| 8 | Intelligence Evaluation & Validation | **Not started** | No evaluation/metrics code anywhere in the repo. |
| 9 | Recommendation Engine | **Not started** | `recommendation_service` is a bare `/health`-only stub. No recommendation table/migration. |
| 10 | Executive Dashboard | **Not started** | `frontend/src/App.tsx` is the default Vite template shell with **three hardcoded static numbers** ("1,245", "12", "Healthy") — not wired to any API. `pages/index.ts` and `components/index.ts` are empty (`export {}`). `api/index.ts` is empty. No charting library, router, or state manager in `package.json` (only `react`/`react-dom`). |
| 11 | Observability & Reliability | **Not started** | `infrastructure/monitoring/` and `infrastructure/observability/` directories exist but are **completely empty** (no files, not even `.gitkeep`). A `shared/logging/logger.py` exists (basic `StreamHandler` + formatter — functional but minimal). No Prometheus/Grafana config, no tracing, no error tracking. Docker Compose healthchecks exist (curl `/health`) — that's the extent of "reliability" tooling. |
| 12 | AI Copilot | **Not started** | `copilot_service` is a bare `/health`-only stub. No `langgraph`/`langchain` dependency anywhere in any `requirements.txt`, confirmed via repo-wide search. |
| 13 | Production Hardening | **Not started** | No JWT/auth/RBAC code anywhere (repo-wide search for `jwt|oauth|authentication|passlib` returns nothing). No `.github/workflows` or any CI config. No caching layer (no Redis in any requirements file). Only one test file exists in the entire backend. |

**Summary: 1 of 13 phases complete, 2 partial (Ingestion, NLP), 10 not started.**

---

## 3. Service-by-Service Reality Check

| Service | Exists | Endpoints beyond `/health` | Core logic | Tests |
|---|---|---|---|---|
| `gateway_service` | Yes | **No** — only `/health` | None. Despite ARCHITECTURE.md/README describing it as the API routing/orchestration entry point, it contains zero routing, proxying, or auth code. | `tests/__init__.py` only (empty) |
| `ingestion_service` | Yes | Yes — `POST /complaints`, `GET /complaints/{id}`, `GET /complaints` (paginated, filterable) | Real: SQLAlchemy model, async repository, Pydantic schemas, hash-based dedup, soft delete, lifecycle-stage updates | `tests/__init__.py` only (empty) — **no tests despite being the most complete service** |
| `nlp_service` | Yes | Yes — `POST /enrichments/process`, `GET /enrichments/{id}`, `GET /enrichments/by-complaint/{id}`, `GET /enrichments` | Real, but heuristic: deterministic keyword-matching classifiers for sentiment/urgency/issue category, not statistical/ML NLP as architecture docs specify | **Yes** — 3 real async tests with mocked dependencies |
| `anomaly_service` | Yes | No — `/health` only | None (stub) | Empty |
| `root_cause_service` | Yes | No — `/health` only | None (stub) | Empty |
| `business_impact_service` | Yes | No — `/health` only | None (stub) | Empty |
| `recommendation_service` | Yes | No — `/health` only | None (stub) | Empty |
| `copilot_service` | Yes | No — `/health` only | None (stub) | Empty |
| `frontend` | Yes | N/A | Default Vite/React template with hardcoded fake metrics; no API integration, no routing, no real pages/components | None |

Note: all 6 stub services share byte-for-byte identical `main.py` boilerplate (DB lifespan check + `/health`) and identical `requirements.txt` (`fastapi`, `uvicorn`, `pydantic-settings`, `sqlalchemy`, `asyncpg`) — they were clearly scaffolded from the same template and never built out.

---

## 4. Data Layer Status

- **SQLAlchemy models vs. CORE_ENTITY_SPECIFICATIONS.md**: Only **2 of the 5+ entities** specified exist as models: `Complaint` (`ingestion_service/app/models/complaint.py`) and `ComplaintEnrichment` (`nlp_service/app/models/complaint_enrichment.py`). Both are well-built — UUID PKs, naming-convention-driven constraints, composite indexes matching the documented analytics query patterns, soft-delete support. Field-level deviations from spec are minor and appear to be deliberate consolidations (e.g., a single `confidence_score` instead of three separate confidence fields; `detected_issue_category` instead of `issue_category`/`issue_subcategory`). **No models exist at all** for: Anomaly Event, Business Impact, Recommendation, Operational Event, and none of the normalization tables from DATABASE_SCHEMA_ARCHITECTURE.md (`complaint_categories`, `severity_levels`, `regions`, `ingestion_jobs`, `complaint_event_links`).
- **Alembic migrations**: 3 migrations exist (`initial_complaint_entity`, `add_complaint_enrichments_table`, `add_explainability_metadata_to_...`), and `migrations/env.py` is correctly wired to async SQLAlchemy + `Base.metadata`. They only cover the 2 tables above — 6+ tables from the schema doc have no migration. Migrations were not executed as part of this audit (no DB running); cannot confirm they apply cleanly, but they read as syntactically consistent with the models.
- **CFPB dataset ingestion**: **Not implemented.** DATASET_AND_INGESTION_STRATEGY.md and MVP_DATASET_SCOPE.md specify the CFPB Consumer Complaint Database (25,000–75,000 records) as the primary dataset. No downloader, no CSV parser, no CFPB field-mapping code exists anywhere in the repo. The only dataset present is `datasets/sample_complaints/operational_seed.json` — **8 hand-authored sample complaints**, clearly synthetic/illustrative, not derived from CFPB.
- **Is any data actually loadable?** Yes, at small scale: `backend/tooling/seed_data/load_sample_complaints.py` is a real, working script that reads the 8-record JSON file and inserts via the repository layer (assuming a running Postgres + applied migrations). This is the only concretely demonstrable "data flow" in the whole system.

---

## 5. Does It Run? (static check only — no installs, no execution)

- **docker-compose.yml**: Internally consistent. All 8 services + postgres + frontend defined; ports match `.env.example`; each service's Dockerfile path, build context, and command exist and match. Healthchecks reference `/health`, which every service does implement.
- **Dockerfiles**: Present for all 8 services, structurally identical (`python:3.11-slim`, copy `backend/shared` + own service dir, `pip install`, `uvicorn` CMD on the documented port). No obvious breakage.
- **requirements.txt**: Present per service, but **`pytest`, `httpx`, and `anyio` are absent from every `requirements.txt`** (including `nlp_service`, which has a test file that imports `pytest` and `httpx`). The one test suite that exists cannot run without manually installing extra packages — there is no root-level `requirements.txt`, `pyproject.toml`, or dev-dependencies file anywhere.
- **`.env` vs `.env.example`**: Identical (byte-for-byte diff shows no difference) — consistent, no missing keys.
- **Imports**: `ingestion_service` and `nlp_service` import from `backend.shared.*` and cross-reference each other's models (e.g., `migrations/env.py` imports both `Complaint` and `ComplaintEnrichment`); paths look correct on inspection. Cannot fully verify without an interpreter run, but no dangling/renamed-module references were found by search.
- **docs/ and infrastructure/**: Both directories exist per REPOSITORY_STRUCTURE.md but their subfolders (`docs/api`, `docs/architecture`, `docs/diagrams`, `docs/workflows`, `docs/deployment`, `infrastructure/docker`, `infrastructure/monitoring`, `infrastructure/deployment`, `infrastructure/observability`) are **completely empty** — no placeholder or content of any kind.
- **notebooks/**: Empty.
- Net assessment: the **2 real services** (ingestion, nlp) plus postgres would very likely start successfully under `docker compose up`. The **6 stub services** would also start (they're valid minimal FastAPI apps) but do nothing. The frontend would start and render its static hardcoded panel. This has not been executed as part of this audit — assessment is based on static file review only.

---

## 6. MVP Gap Analysis

ROADMAP.md §4 defines MVP scope as: `ingestion_service`, `nlp_service`, `anomaly_service`, `gateway_service` (backend) + complaint dashboard/trend viz/anomaly alerts (frontend) + basic copilot querying (AI).

Ordered by dependency, what stands between current state and a demoable MVP:

1. **Real dataset ingestion** — replace the 8-record sample with actual CFPB data loading (download/parse/map/persist at the documented 25K–75K scale). Everything downstream (anomaly detection, dashboards, believable demo) depends on having enough real, time-distributed data to show trends. *This is the single highest-leverage gap.*
2. **`operational_events` table + synthetic event generator** — required by Phase 2 and by the root-cause/anomaly correlation story that differentiates this platform from a plain complaint tracker; currently entirely absent.
3. **`anomaly_service` implementation** — spike/trend detection logic, consuming the (currently nonexistent at scale) complaint volume data. Explicitly in MVP scope; currently a `/health`-only stub.
4. **`gateway_service` implementation** — currently does not route to any downstream service; a "gateway" that only answers its own `/health` cannot serve as the frontend's single entry point as ARCHITECTURE.md and the README's port table both assume.
5. **Frontend wiring** — replace the hardcoded static panel with real API calls (needs `gateway_service` to function first), plus a charting library (none installed) for trend visualization and anomaly alerts.
6. **Basic copilot querying** — `copilot_service` is an empty stub with no LLM/LangGraph dependency declared anywhere; this is the least-started MVP component (0% built) but is last in the MVP's own stated dependency order.
7. *(Not in ROADMAP §4 MVP scope but implied by "believable" demo)*: at minimum a way to `docker compose up` and manually verify the loop end-to-end has not been demonstrated in this audit — worth a real run before claiming any of the above "works."

Not required for MVP per ROADMAP.md, correctly deferred: `root_cause_service`, `business_impact_service`, `recommendation_service`, observability stack, auth/JWT, CI/CD — all appropriately left at 0%.

---

## 7. Bottom Line

Roughly **20–25% of the stated MVP is real**: solid, well-engineered ingestion and rule-based NLP enrichment services with clean async SQLAlchemy models, sensible indexing, and (for NLP) an actual test suite — this part is not fake scaffolding, it's genuine working code. Everything else — anomaly detection, the gateway that's supposed to unify the API surface, the dashboard, and the copilot — is either an empty `/health`-only stub or a static mockup with hardcoded numbers. The single biggest gap is **data**: the entire intelligence pipeline (anomaly detection, trends, root cause, business impact, dashboards) is documented and designed around the CFPB dataset at 25K–75K-record scale, but the only data in the repository is 8 hand-written sample complaints — so even if every stub service were filled in tomorrow, there is currently nothing at realistic scale for those services to operate on or for a dashboard to meaningfully visualize.
