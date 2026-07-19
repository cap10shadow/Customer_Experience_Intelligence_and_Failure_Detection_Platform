
# CHANGELOG

All notable engineering changes to the Customer Experience Intelligence & Failure Detection Platform are documented in this file.

The format follows a simplified version of the Keep a Changelog convention.

---

# 2026-07-19

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

**Phase 5 – Trend & Anomaly Detection**

- Complaint trend analysis.
- Spike detection.
- Regional monitoring.
- Issue clustering.
- Anomaly APIs.
