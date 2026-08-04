# Customer Experience Intelligence & Failure Detection Platform

A Customer Experience Intelligence & Operational Decision Support Platform (per the Architecture Review Board, `docs/ADR_ARCHITECTURE_REVIEW_BOARD.md`, ADR-001) that ingests customer signals, detects anomalies, correlates incidents, identifies root causes, and surfaces actionable recommendations for operational teams. It is NOT merely a complaint analytics dashboard — its purpose is to transform customer complaints into explainable operational intelligence and evidence-based business decisions.

---

## Current Implementation Status

**Phase 1 through Phase 9 are fully IMPLEMENTED.** The core data ingestion, NLP enrichment, anomaly detection, incident correlation, root cause analysis, business impact analysis, intelligence evaluation engines, and the recommendation engine are all operational.

**Phase 10 (Executive Dashboard) is the active development phase.** Phase 10 Step 1 (Product Workspace Architecture) and Step 2 (Dashboard Information Architecture) are now complete. Phase 10 Step 3 is next; its scope is not yet defined.

**Phase 11+ (Observability & Reliability, AI Copilot, Production Hardening) are PLANNED FUTURE PHASES.**

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

### In Progress
- ↓
- **Executive Dashboard** (Steps 1–2 Complete)

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
| gateway_service | 8000 | API routing and request orchestration | Implemented |
| ingestion_service | 8001 | Data ingestion and validation | Implemented |
| nlp_service | 8002 | NLP enrichment pipeline | Implemented |
| anomaly_service | 8003 | Anomaly detection & Incident Correlation | Implemented |
| root_cause_service | 8004 | Root cause correlation | Stable |
| business_impact_service | 8005 | Business impact estimation | Stable |
| recommendation_service | 8006 | Recommendation generation | Stable |
| copilot_service | 8007 | AI copilot and natural-language querying | Scaffolded / Planned |
| evaluation_service | 8008 | Intelligence quality & explainability assurance (out-of-band, event-driven) | Stable |
| frontend | 3000 | Operational dashboard | Dashboard Information Architecture Complete |

Each service exposes a `/health` endpoint.

---

## Technology Stack

- **Backend:** FastAPI (Python), REST APIs
- **Database:** PostgreSQL, SQLAlchemy 2.x, Alembic
- **Infrastructure:** Docker, Docker Compose
- **Intelligence:** Deterministic rules, Scikit-learn (planned), LangGraph (planned)
- **Frontend:** React, TypeScript, React Router (application shell, workspace routing, and Dashboard information architecture implemented)

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
