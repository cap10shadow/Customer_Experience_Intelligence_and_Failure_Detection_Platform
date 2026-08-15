# Early Design Specifications

These eight documents are the platform's original, pre-implementation design specifications. They are preserved for the engineering reasoning and design philosophy they contain — but **they do not describe the system as it was actually built**, and should not be read as current reference material. Where they conflict with the actual codebase, migrations, or the documents listed under "Current authority" below, the actual implementation and those documents govern.

## Why these are historical, not current

Read against the actual implementation (`backend/services/*/app/models/`, `backend/migrations/versions/`, `backend/shared/constants/enums/`), each of these documents proposes entities, tables, or a dataset strategy that the project ultimately built differently:

- `CORE_ENTITY_SPECIFICATIONS.md`, `DATABASE_SCHEMA_ARCHITECTURE.md`, `DATA_MODEL.md`, `ENTITY_MODELING_AND_OWNERSHIP.md` all propose a shared, normalized relational schema (`operational_events`, `business_impacts`, `complaint_categories`, `severity_levels`, `regions`, `ingestion_jobs`, `complaint_event_links`, `anomaly_events`, `churn_risk_assessments`, and similar). None of these tables exist. The platform instead evolved into one table per owning service (`complaints`, `complaint_enrichments`, `incidents`/`active_anomalies`/`anomaly_history`, `root_causes`, `business_impact_assessments`, `recommendations`/`recommendation_decision_history`, `evaluations`, `users`/`roles`/`user_roles`, `copilot_conversations`/`copilot_messages`) — a materially different, later design.
- `DATASET_AND_INGESTION_STRATEGY.md` and `MVP_DATASET_SCOPE.md` recommend the CFPB Consumer Complaint Database (25,000–75,000 records) plus a synthetic operational-event generator service. Neither was built — actual seed/validation data is a small set of hand-written sample and synthetic complaints (`datasets/sample_complaints/`, `datasets/validation/`).
- `DOMAIN_ENUMS_AND_OPERATIONAL_CONSTANTS.md` proposes enum vocabularies (e.g. a nine-value complaint-status lifecycle) that don't match the actual enums in `backend/shared/constants/enums/`. One section (Confidence Philosophy) was updated during a later architecture review and remains accurate — see `docs/DECISIONS.md`'s ADR-008.
- `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md` is the most current of the eight — it was partially revised during the Architecture Review Board session (`docs/CHANGELOG.md`, "Terminology aligned," "Business Impact Engine framing corrected," "Incident's role... clarified") and its root-cause/business-impact/evaluation sections reference real ADRs and real table names. Its `recommendation_service` and `copilot_service` sections are still stale, describing both as minimal/future-oriented; both are now fully implemented.

`docs/CHANGELOG.md` itself records that six of these eight (all but `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md` and the one `DOMAIN_ENUMS_AND_OPERATIONAL_CONSTANTS.md` section) were deliberately left unchanged during that review as out of scope at the time — this was a conscious deferral, not an oversight, and it is being resolved now by this relocation and this note.

## Current authority

For how the platform actually works today, use:

| Concern | Authoritative document |
|---|---|
| System architecture, service list | [`ARCHITECTURE.md`](../../ARCHITECTURE.md), [`docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md`](../architecture/phase-13/PHASE_13_ARCHITECTURE.md) |
| Architecture decisions & reasoning | [`docs/DECISIONS.md`](../DECISIONS.md) |
| Actual database schema | `backend/migrations/versions/` (Alembic — the only real schema authority) and each service's `app/models/` |
| Actual domain enums | `backend/shared/constants/enums/` |
| Current implementation status | [`docs/PROJECT_STATUS.md`](../PROJECT_STATUS.md) |
| Project overview | [`README.md`](../../README.md) |

## What's here

| Document | Original scope |
|---|---|
| `CORE_ENTITY_SPECIFICATIONS.md` | Proposed core operational entities (Complaint, Enrichment, Anomaly Event, Business Impact, Recommendation) |
| `DATABASE_SCHEMA_ARCHITECTURE.md` | Proposed relational schema, tables, and indexing strategy |
| `DATA_MODEL.md` | Proposed domain entity model and relationships |
| `DATASET_AND_INGESTION_STRATEGY.md` | Proposed real + synthetic dataset sourcing strategy |
| `DOMAIN_ENUMS_AND_OPERATIONAL_CONSTANTS.md` | Proposed shared enum vocabulary |
| `ENTITY_MODELING_AND_OWNERSHIP.md` | Proposed entity categories and service ownership philosophy |
| `MVP_DATASET_SCOPE.md` | Proposed MVP dataset selection and sizing |
| `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md` | Service responsibility and persistence-ownership philosophy (partially updated, most current of the eight) |
