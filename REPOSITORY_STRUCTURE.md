# Repository Structure

# Customer Experience Intelligence & Failure Detection Platform

---

# 1. Purpose Of This Document

This document answers one question:

> "Where do things live, and what does each major area of the repository contain?"

It is not the architecture reference. For architecture, product, and status information, see:

- **[README.md](README.md)** — primary project overview and onboarding entry point
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — stable, high-level architecture overview
- **[docs/architecture/](docs/architecture/)** — detailed, phase-by-phase architecture records
- **[docs/DECISIONS.md](docs/DECISIONS.md)** — formal architecture decision records (ADRs)
- **[docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)** — current project status and known gaps
- **[ROADMAP.md](ROADMAP.md)** — forward-looking direction
- **[docs/design/](docs/design/)** — early, pre-implementation design specifications; each document is explicitly labeled historical/superseded where the implementation diverged from the original spec (see `docs/design/README.md`)

---

# 2. Root-Level Structure

```
project-root/
│
├── backend/                    Backend services, shared code, migrations, tooling
├── frontend/                   React/TypeScript single-page application
├── docs/                       Engineering, architecture, and process documentation
├── infrastructure/             Docker, monitoring, and deployment configuration
├── datasets/                   Sample data and validation tooling
├── .github/                    CI workflow definitions
│
├── docker-compose.yml          Local development orchestration
├── docker-compose.prod.yml     Hardened production orchestration
├── alembic.ini                 Root Alembic configuration (backend migrations)
├── .env.example                Template for local environment configuration
├── .gitignore / .dockerignore  Ignore rules for version control / image builds
│
├── README.md                   Project overview and onboarding
├── ARCHITECTURE.md             Stable architecture overview
├── PRD.md                      Product requirements
├── PROJECT_BRAIN.md            Original pre-implementation vision (historical)
├── PRODUCT_EXPERIENCE_GUIDE.md Product/UX behavior specification
├── ROADMAP.md                  Forward-looking roadmap
└── REPOSITORY_STRUCTURE.md     This document
```

---

# 3. backend/

```
backend/
├── services/        The nine backend services (see below)
├── shared/          Code shared across services
├── migrations/       Alembic migrations for the platform database
├── tooling/         Developer and operational tooling (not part of the runtime API surface)
└── requirements-test.txt
```

## 3.1 backend/services/

Each service is an independently runnable FastAPI application with its own `app/`, `tests/`, `Dockerfile`, and `requirements.txt`:

- `anomaly_service/`
- `business_impact_service/`
- `copilot_service/`
- `evaluation_service/`
- `gateway_service/`
- `ingestion_service/`
- `nlp_service/`
- `recommendation_service/`
- `root_cause_service/`

Internal organization of `app/` varies by service (some use a flatter `api/core/models/services/schemas` layout, others use a more explicit hexagonal `application/domain/infrastructure/presentation` layout) — see [ARCHITECTURE.md](ARCHITECTURE.md) and `docs/architecture/` for details on each service's design.

## 3.2 backend/shared/

Code intended for reuse across services: `config/`, `constants/`, `contracts/`, `database/`, `logging/`, `observability/`, `schemas/`, `security/`, `utils/`, plus its own `tests/`.

## 3.3 backend/migrations/

Alembic migration environment (`env.py`, `script.py.mako`) and the `versions/` directory containing the platform's sequential database migrations. Historical migrations are not modified after merge.

## 3.4 backend/tooling/

Developer/operational tooling, kept separate from service runtime code:

- `backup_restore/` — database backup and restore tooling
- `diagnostics/` — persistence and system diagnostics scripts
- `seed_data/` — seed data utilities
- `benchmarking/`, `dataset_generators/`, `local_dev/` — reserved for future tooling; currently placeholders

---

# 4. frontend/

```
frontend/
├── src/
│   ├── app/           Routing, providers, layouts, theme, configuration
│   ├── auth/          Authentication
│   ├── copilot/       Copilot feature module
│   ├── shared/        Shared components, hooks, types, utilities, icons, constants
│   ├── workspaces/    Feature workspaces: administration, analytics, dashboard,
│   │                  ingestion, investigations, recommendations
│   ├── tests/         Frontend test suite
│   └── main.tsx
│
├── public/
├── package.json / package-lock.json
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
├── vite.config.ts
├── eslint.config.js
├── Dockerfile / nginx.conf
└── README.md          Frontend-specific setup notes
```

Each entry under `workspaces/` follows a consistent internal shape: `api/`, `components/`, `context/`, `hooks/`.

---

# 5. docs/

```
docs/
├── ADR_ARCHITECTURE_REVIEW_BOARD.md   Formal architecture review board record (authoritative on conflicts)
├── DECISIONS.md                       Architecture decision records (ADRs)
├── CHANGELOG.md                       Chronological engineering changelog
├── ENGINEERING_WORKFLOW.md            Team workflow standard
├── PROJECT_STATUS.md                  Live project status and known-gap tracker
├── VALIDATION_REPORT.md               End-to-end synthetic-data validation record and completion assessment
│
├── architecture/                      Phase-by-phase architecture records (see below)
└── design/                            Early design specifications (see below)
```

## 5.1 docs/architecture/

Contains one directory per architecture phase (`phase-10/`, `phase-11/`, `phase-12/`, `phase-13/`), documenting the platform's architecture as it evolved. `docs/architecture/phase-10/history/` holds superseded drafts, explicitly marked non-authoritative with a pointer to the current record.

## 5.2 docs/design/

Early, pre-implementation design specifications (data model, entity modeling, dataset strategy, etc.). Where the shipped implementation diverged from a given spec, that document is explicitly annotated as historical — see `docs/design/README.md` for the current-vs-historical breakdown of each file.

---

# 6. infrastructure/

```
infrastructure/
├── docker/
├── monitoring/
├── deployment/
└── observability/
```

Docker, monitoring (e.g. Prometheus/Grafana), deployment, and observability configuration, kept separate from application code.

---

# 7. datasets/

```
datasets/
├── sample_complaints/     Hand-written sample complaint data used for local development/seeding
└── validation/            Synthetic-data validation harness (run_validation.py) used for
                            scenario-based platform validation
```

---

# 8. .github/

```
.github/
└── workflows/
    └── ci.yml     Continuous integration workflow
```

---

# 9. Root Configuration Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Local development orchestration for all services |
| `docker-compose.prod.yml` | Hardened production orchestration |
| `alembic.ini` | Root Alembic configuration for backend migrations |
| `.env.example` | Template for required environment variables (no real secrets) |
| `.gitignore` | Version control ignore rules |
| `.dockerignore` | Docker build-context ignore rules |
