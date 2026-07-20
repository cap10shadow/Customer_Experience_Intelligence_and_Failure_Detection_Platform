# Customer Experience Intelligence & Failure Detection Platform

An operational intelligence platform that ingests customer signals, detects anomalies, correlates incidents, identifies root causes, and surfaces actionable recommendations for operational teams.

---

## Current Implementation Status

**Phase 1 through Phase 5 are fully IMPLEMENTED.** The core data ingestion, NLP enrichment, anomaly detection, and incident correlation engines are operational.

**Phase 6+ (Root Cause Analysis, AI Copilot, Recommendations) are PLANNED FUTURE PHASES.**

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

### Planned Future Phases
- ↓
- **Root Cause Analysis**
- ↓
- **Business Impact Analysis**
- ↓
- **Recommendation Engine**
- ↓
- **AI Copilot**

---

## Current Architecture & Module Overview

The platform uses a modular, service-based architecture sharing a single repository and database.

| Service | Port | Responsibility | Status |
|---------|------|----------------|--------|
| gateway_service | 8000 | API routing and request orchestration | Implemented |
| ingestion_service | 8001 | Data ingestion and validation | Implemented |
| nlp_service | 8002 | NLP enrichment pipeline | Implemented |
| anomaly_service | 8003 | Anomaly detection & Incident Correlation | Implemented |
| root_cause_service | 8004 | Root cause correlation | Scaffolded / Planned |
| business_impact_service | 8005 | Business impact estimation | Scaffolded / Planned |
| recommendation_service | 8006 | Recommendation generation | Scaffolded / Planned |
| copilot_service | 8007 | AI copilot and natural-language querying | Scaffolded / Planned |
| frontend | 3000 | Operational dashboard | Scaffolded / Planned |

Each service exposes a `/health` endpoint.

---

## Technology Stack

- **Backend:** FastAPI (Python), REST APIs
- **Database:** PostgreSQL, SQLAlchemy 2.x, Alembic
- **Infrastructure:** Docker, Docker Compose
- **Intelligence:** Deterministic rules, Scikit-learn (planned), LangGraph (planned)
- **Frontend:** React, TypeScript (planned)

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
