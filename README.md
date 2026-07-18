# Customer Experience Intelligence & Failure Detection Platform

An operational intelligence platform that ingests customer signals, detects anomalies,
identifies root causes, and surfaces actionable recommendations for operational teams.

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

## Services

| Service | Port | Responsibility |
|---------|------|----------------|
| gateway_service | 8000 | API routing and request orchestration |
| ingestion_service | 8001 | Data ingestion and validation |
| nlp_service | 8002 | NLP enrichment pipeline |
| anomaly_service | 8003 | Anomaly and trend detection |
| root_cause_service | 8004 | Root cause correlation |
| business_impact_service | 8005 | Business impact estimation |
| recommendation_service | 8006 | Recommendation generation |
| copilot_service | 8007 | AI copilot and natural-language querying |
| frontend | 3000 | Operational dashboard |

Each service exposes a `/health` endpoint.

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
