# Customer Experience Intelligence & Failure Detection Platform

A Customer Experience Intelligence & Operational Decision Support Platform (per the Architecture Review Board, `docs/ADR_ARCHITECTURE_REVIEW_BOARD.md`, ADR-001) that ingests customer signals, detects anomalies, correlates incidents, identifies root causes, and surfaces actionable recommendations for operational teams. It is NOT merely a complaint analytics dashboard — its purpose is to transform customer complaints into explainable operational intelligence and evidence-based business decisions.

---

## Current Implementation Status

**Phase 1 through Phase 9 are fully IMPLEMENTED.** The core data ingestion, NLP enrichment, anomaly detection, incident correlation, root cause analysis, business impact analysis, intelligence evaluation engines, and the recommendation engine are all operational.

**Phase 10 (Executive Dashboard) is COMPLETE across all seven steps, followed by an intermediate capability-completion step (Step 7.X, COMPLETE).** Steps 1–6 established the five-workspace frontend architecture (Dashboard, Investigations, Recommendations, Analytics, Administration); following a Product Architecture Review, Action Center was retired as a standalone workspace and its responsibility absorbed into Recommendations (see `docs/DECISIONS.md`, FE-001). Step 7 connected that architecture to real backend intelligence through a centralized Gateway: Dashboard, Investigation, Recommendation (read), and Analytics (trends) render real data end to end, and Business Impact assessments publish a `BusinessImpactCompleted` event consumed independently by Recommendation and Evaluation.

Step 7.X then closed the gap between Step 7's real-data integration and a small set of genuinely missing or dishonestly-presented capabilities identified in a follow-up audit: Dashboard Supporting Evidence and the partial-failure `warnings` signal are now real; Business Impact carries its own ARB-008-compliant confidence classification; Investigation's Evidence section can surface a real, dimension-scoped NLP aggregate; Analytics' Executive Overview and its three narrative sections (Pattern Discovery, Organizational Insights, Strategic Opportunities) are now honest — either a real rollup or an explicit future-capability placeholder, never fabricated narrative; Administration's Platform Overview shows real service health; **Recommendation Decision is now a real, persisted capability** (approve/reject/defer/pending plus an optional note, no decision-owner/actor — see `docs/DECISIONS.md`, REC-003); and **Administration's Intelligence Configuration now displays real, read-only Business Impact engine values** (weights, point values, severity bands) sourced live from `business_impact_service`, with no edit/save/mutation control anywhere.

Still explicitly deferred: Root Cause confirm/reject/refresh (a write capability), `RecommendationStatisticsService` surfacing, full Dashboard dimensional filtering (region/business unit/product/user), Administration User & Access Management, Administration Audit & Change History persistence, editable/persisted Intelligence Configuration, Recommendation Effectiveness/outcome tracking, and an Evaluation Service UI (explicitly decided against — see `docs/architecture/phase-10/STEP_7X_SCOPE_FREEZE.md`). Event delivery remains single-attempt/best-effort (no message broker, Outbox, or durable retry), and there is no authentication/RBAC anywhere in the platform yet — the new `PATCH` decision endpoint is exactly as unauthenticated as every other Gateway route today. See `ROADMAP.md` and `docs/DECISIONS.md` for the full list of what remains deferred.

**Phase 11 (Observability & Reliability) is COMPLETE.** Structured JSON logging, `X-Request-ID` correlation, Prometheus HTTP metrics, liveness/readiness health, OpenTelemetry distributed tracing (Tempo), and a Grafana operational-visualization layer (two dashboards — Platform Health, API & Service Performance) are live across all 9 backend services, verified against real running services. A third dashboard originally scoped ("Intelligence Pipeline") was explicitly deferred rather than built on fabricated data — it requires domain metrics (anomalies detected, recommendations generated, etc.) that no Phase 11 batch ever implemented; see `docs/DECISIONS.md` (OBS-002). This is an internal operator/infrastructure surface only — no frontend workspace, Gateway route, or user-facing feature was added.

**Phase 12+ (AI Copilot, Production Hardening) are PLANNED FUTURE PHASES.**

The Evaluation Service (Phase 8) is an independent Intelligence Assurance Service, not part of the linear pipeline below: it observes completed intelligence out-of-band, event-driven, and never modifies or blocks any upstream service.

---

## Intelligence Pipeline

### Implemented
- **Complaint Data**
- ↓
- **Ingestion** (Validation & Normalization)
- ↓
- **NLP Intelligence** (Classification & Sentiment)
- ↓
- **Trend Analysis** (Metrics Aggregation)
- ↓
- **Anomaly Detection** (Spikes & Fingerprints)
- ↓
- **Incident Correlation** (Grouping Anomalies)
- ↓
- **Root Cause Analysis** (Deterministic Rules, Lifecycle & Persistence)
- ↓
- **Business Impact Analysis** (Deterministic Rules, Persistence & Lifecycle)
- ↓
- **Recommendation Engine** (Deterministic Rules, Persistence & Lifecycle)
- ↓
- **Executive Dashboard** (Steps 1–7 Complete — Gateway/API integration, real workspace data, BusinessImpactCompleted event fan-out; Step 7.X Complete — Recommendation Decision persistence, read-only Intelligence Configuration, and further real-data/honesty completions)

### Planned Future Phases
- ↓
- **AI Copilot**

### Long-Term Vision (Post-MVP, Not Currently Scheduled)

Per the Architecture Review Board (ADR-002), the platform's long-term architectural vision extends this pipeline beyond Recommendation Engine and AI Copilot into a complete intelligence lifecycle: **Recommendation → Human Action → Outcome → Organizational Knowledge → Continuous Improvement**. This is a long-term direction only — it does not add phases to the roadmap above or change current MVP scope. See `docs/ADR_ARCHITECTURE_REVIEW_BOARD.md` for details.

---

## Current Architecture & Module Overview

The platform uses a modular, service-based architecture sharing a single repository and database.

| Service | Port | Responsibility | Status |
|---------|------|----------------|--------|
| gateway_service | 8000 | API routing, aggregation, and request orchestration for the frontend | Implemented — public boundary for Dashboard/Investigation/Recommendation/Analytics |
| ingestion_service | 8001 | Data ingestion and validation | Implemented |
| nlp_service | 8002 | NLP enrichment pipeline | Implemented |
| anomaly_service | 8003 | Anomaly detection & Incident Correlation | Implemented |
| root_cause_service | 8004 | Root cause correlation | Stable |
| business_impact_service | 8005 | Business impact estimation; publishes `BusinessImpactCompleted` | Stable |
| recommendation_service | 8006 | Recommendation generation; consumes `BusinessImpactCompleted` | Stable |
| copilot_service | 8007 | AI copilot and natural-language querying | Scaffolded / Planned |
| evaluation_service | 8008 | Intelligence quality & explainability assurance (out-of-band, event-driven); consumes `BusinessImpactCompleted` | Stable |
| frontend | 3000 | Operational dashboard | Dashboard, Investigation, Recommendation (read + decision persistence), and Analytics (trends) integrated with real Gateway data; Administration integrated for Platform Overview and read-only Intelligence Configuration, otherwise presentation-only |

Each service exposes a `/health` endpoint.

---

## Technology Stack

- **Backend:** FastAPI (Python), REST APIs
- **Database:** PostgreSQL, SQLAlchemy 2.x, Alembic
- **Infrastructure:** Docker, Docker Compose
- **Intelligence:** Deterministic rules, Scikit-learn (planned), LangGraph (planned)
- **Frontend:** React, TypeScript, React Router — application shell, five-workspace architecture, and centralized Gateway API client, integrated with real backend data for Dashboard, Investigation, Recommendation (read + decision persistence), Analytics (trends), and Administration (Platform Overview + read-only Intelligence Configuration)

---

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Run

```bash
cp .env.example .env
docker compose up --build
```

---

## Repository Layout

```
backend/
├── services/        # One directory per intelligence service
├── shared/          # Config, logging, schemas, contracts, utils, constants
├── migrations/      # Database migrations (Alembic)
├── scripts/         # Operational scripts
└── tooling/         # Seed data, dataset generators, local dev utilities

frontend/            # React + TypeScript dashboard
infrastructure/      # Docker, monitoring, observability configs
datasets/            # Raw and processed datasets
notebooks/           # Exploratory analysis
docs/                # Architecture, API, workflow documentation
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and service responsibilities |
| [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) | Directory conventions and engineering standards |
| [PRD.md](PRD.md) | Product requirements |
| [ROADMAP.md](ROADMAP.md) | Development roadmap |
| [PROJECT_BRAIN.md](PROJECT_BRAIN.md) | Engineering context and decisions |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records (ADRs) |
| [docs/ADR_ARCHITECTURE_REVIEW_BOARD.md](docs/ADR_ARCHITECTURE_REVIEW_BOARD.md) | Architecture Review Board session record |
