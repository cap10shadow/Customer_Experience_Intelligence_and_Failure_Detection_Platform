
# CHANGELOG

All notable engineering changes to the Customer Experience Intelligence & Failure Detection Platform are documented in this file.

The format follows a simplified version of the Keep a Changelog convention.

---

# 2026-07-22

## Phase 7 – Step 1 (Business Impact Analysis Engine)

Phase 7 Step 1 has been fully completed, delivering a pure, deterministic Business Impact Analysis Engine. The engine evaluates an Incident and its identified Root Cause across five business dimensions to produce an immutable, fully explainable `BusinessImpactAssessment`.

### Added

- **Business Impact Analysis Engine** — deterministic orchestration engine accepting an injected sequence of `ImpactRule` instances.
- **`ImpactRule` abstraction** — abstract base class placed in the domain layer enforcing a single evaluation contract per rule.
- **`FinancialRule`** — evaluates financial impact based on root cause type and complaint volume growth.
- **`CustomerRule`** — evaluates customer impact based on estimated affected customer count and urgency.
- **`OperationalRule`** — evaluates operational impact based on root cause type and anomaly severity.
- **`SLARule`** — evaluates SLA impact based on SLA breach count and urgency annotations.
- **`ReputationRule`** — evaluates reputational impact based on sentiment ratio, confirmed sentiment shifts, and multi-region spread.
- **`ImpactEvaluation`** — immutable value object carrying dimension, level, and deterministic reason string.
- **`BusinessImpactProfile`** — structured container for all five named `ImpactEvaluation` fields with an `all_evaluations()` helper.
- **`BusinessImpactAssessment`** — immutable final domain output with the exact 13 specified fields. No ORM metadata. No timestamps.
- **Centralized weighting** — `weighting.py` centralizes dimension weights (Financial 35%, Customer 25%, Operational 15%, SLA 15%, Reputation 10%).
- **Deterministic explanation generation** — `explanation.py` aggregates `ImpactEvaluation` reason strings without duplicating business logic.
- **`scoring.py`** — centralizes level-to-points conversion, weighted aggregation, severity band mapping, priority assignment, and the completeness-based confidence heuristic.
- **Local input value objects** — `Incident`, `RootCauseSummary`, `TrendMetrics`, `AnomalyMetrics` as persistence-independent domain inputs, consistent with the service-isolation convention established in Phase 6 (RCA-001).

### Testing

- 85 new unit tests added covering all domain models, rules, engine orchestration, scoring, weighting, and explanation.
- **356 / 356** total repository tests passing (271 pre-existing + 85 new).
- mypy clean across 31 files in the new module.

### Verification

- Architecture reviewed by Principal Software Architect prior to implementation.
- Architecture reviewed post-implementation. No architectural drift identified.
- Zero modified files — all prior-phase code, tests, and APIs remain completely untouched.
- Phase officially frozen.

---

# 2026-07-21

## Phase 6 Complete (Root Cause Analysis)

Phase 6 has been fully completed, delivering a deterministic, explainable Root Cause Analysis engine that is now fully integrated into the platform with persistence, REST APIs, and operational lifecycle management.

### Major Capabilities Introduced:
- **Deterministic Rule Engine:** Specification-pattern rules evaluate Incidents and produce fully explainable RootCauseCandidates.
- **Persistence & APIs:** Root Cause records are persisted in PostgreSQL with a complete REST API surface.
- **Lifecycle Management:** Root Causes can be confirmed, rejected, or recalculated via explicit lifecycle transitions enforced by the LifecycleValidator.

---

## Phase 6 – Step 3

### Added

- Lifecycle Validator with deterministic state machine enforcement.
- Confirm operation (`PATCH /api/v1/root-causes/{id}/confirm`).
- Reject operation (`PATCH /api/v1/root-causes/{id}/reject`).
- Refresh/Recalculation operation (`POST /api/v1/root-causes/{id}/refresh`).
- Terminal state protection (CONFIRMED and REJECTED states are protected from invalid transitions).
- UNKNOWN result handling on refresh (explicit handling when Rule Engine returns no matching candidate).

### Verified

- Lifecycle transition unit tests passing.
- Invalid transition rejection tests passing.
- Integration tests for all three new endpoints.
- Full repository regression suite passing.
- End-to-end pipeline validated via Docker and PostgreSQL.
- Rule Engine confirmed completely unchanged.

---

## Phase 6 – Step 2

### Added

- RootCause persistence layer (SQLAlchemy model, JSON evidence, Alembic migration).
- RootCause and Incident Read Repositories maintaining CRUD boundaries.
- Mapper layer (`RootCauseMapper`, `IncidentMapper`) to strictly isolate Domain logic from ORM objects.
- `RootCauseApplicationService` to orchestrate mapping, inference, and persistence.
- REST APIs (`POST /api/v1/root-causes`, `GET /api/v1/root-causes/{id}`, etc.).

### Verified

- 26 integration tests and 232 repository tests passing.
- Complete end-to-end Root Cause pipeline validated via Docker and PostgreSQL.
- Strict adherence to Clean Architecture and DATA-002 (no ORM leakage into the Domain Engine).

---

## Phase 6 – Step 1

### Added

- Deterministic Root Cause Rule Engine.
- Specification Pattern for rule evaluation.
- `RuleRegistry` and Rule Versioning.
- `RootCauseCandidate` domain object.
- Structured Evidence and Confidence scoring models.
- Five independent deterministic rules (Payment, Logistics, Service Outage, Inventory, Customer Support).
- Persistence-independent `Incident` domain input model.

### Verified

- 56/56 new unit tests passed.
- 210/210 full repository tests passed.
- Smoke tests and Pyflakes checks passed.
- Pure in-memory domain logic (no SQLAlchemy, ORM, APIs, or dependency injection).

---

# 2026-07-20

## Phase 5 Complete (Trend, Anomaly & Incident Correlation)

Phase 5 has been fully completed, successfully introducing the platform's core operational intelligence engine. The Anomaly Service is now stable and capable of detecting emerging risks before escalating them to the future Root Cause Engine.

### Major Capabilities Introduced:
- **Trend Analysis:** Real-time metrics aggregation across volumes, sentiments, and urgencies.
- **Anomaly Detection:** Deterministic spike detection with lifecycle tracking and stable fingerprinting.
- **Incident Correlation:** Grouping related anomalies into higher-level incidents, reducing noise and focusing investigations.

---

## Phase 5 – Step 3

### Added
- Incident Correlation Engine
- Incident grouping logic for related anomalies
- Transition structures preparing for Phase 6 Root Cause Analysis

---

## Phase 5 – Step 2

### Added

- Active anomaly lifecycle management
- Historical anomaly tracking
- Fingerprint-based identity
- Explainability layer
- Five deterministic detectors
- REST API endpoints
- Alembic migration

### Changed

- Centralized severity model
- New anomaly enums

### Validation

- Live Docker verification
- PostgreSQL migration verification
- OpenAPI verification
- Full test suite passing

---

# 2026-07-19

## Phase 5 – Step 1

### Added

- Trend Analysis Engine (`TrendEngine`) for the Anomaly Service, orchestrating five modular aggregators.
- Modular aggregators: `VolumeAggregator`, `CategoryAggregator`, `RegionAggregator`, `SentimentAggregator`, `UrgencyAggregator` — each with a single responsibility.
- `TrendRepository` for read-only, SQL-side aggregation queries against `complaints` and `complaint_enrichments`.
- Six read-only trend endpoints: `/trends`, `/trends/daily`, `/trends/categories`, `/trends/regions`, `/trends/sentiment`, `/trends/urgency`.
- Architectural decision DATA-002 for service-local read models.

### Changed

- Registered the trends router in the Anomaly Service's application entrypoint.

### Verified

- Full Anomaly Service test suite and full-repository test suite passing.
- Docker Compose build and startup for the Anomaly Service alongside Postgres, the Ingestion Service, and the NLP Service.
- OpenAPI schema generation.
- All six trend endpoints against real seeded and NLP-enriched data.
- No database changes: metrics are computed dynamically from existing tables, with no new migrations.

### Notes

- Purely descriptive, explainable analytics — no anomaly detection, severity scoring, or persistence introduced in this step; reserved for Phase 5 Step 2.

---

## Phase 4 – Step 4

### Added

- Architectural decision DATA-001 for database-level referential integrity across boundaries.

### Changed

- Replaced monolithic `classifiers.py` and `text_processing.py` utilities with decoupled modular services (`SentimentAnalyzer`, `UrgencyAnalyzer`, `CategoryClassifier`, `KeywordExtractor`, `Summarizer`).
- Ensured deterministic orchestration service captures explainability metadata effectively.

### Fixed

- Removed all dead code and imports related to deprecated NLP utility modules.

### Verified

- Full test suite execution.
- Docker builds and API schema loading.
- Explainability metadata persistence.
- Project documentation updates.

---

## Phase 4 – Step 3

### Added

- Complaint enrichment REST API.
- Idempotent complaint processing.
- Explainability metadata persistence.
- Pagination support for enrichment retrieval.

### Changed

- Improved complaint enrichment workflow.
- Refined API response handling.
- Updated service architecture to support future NLP expansion.

### Fixed

- Removed ORM relationship coupling between `Complaint` and `ComplaintEnrichment`.
- Resolved SQLAlchemy mapper initialization issue.
- Fixed AsyncSession concurrency caused by parallel repository calls.

### Verified

- Docker Compose startup.
- Service health endpoints.
- Swagger/OpenAPI documentation.
- Complaint enrichment API.
- Database persistence.
- Runtime logs.
- Unit and integration tests.

---

# Previous Milestones

## Phase 1 – Foundation

### Completed

- Project scaffolding.
- Shared infrastructure.
- Configuration management.
- Logging framework.
- Docker environment.

---

## Phase 2 – Data Layer

### Completed

- Database architecture.
- SQLAlchemy models.
- Alembic migrations.
- Repository layer.

---

## Phase 3 – Ingestion Layer

### Completed

- Complaint ingestion pipeline.
- Validation.
- Persistence.
- Duplicate detection.
- API endpoints.

---

## Upcoming

The next planned milestone is:

**Phase 7 Step 2 – Business Impact Persistence & APIs**

- ORM model for `BusinessImpactAssessment`.
- Alembic migration.
- Repository layer.
- Mapper from persisted domain records into engine input value objects.
- REST API endpoints.
