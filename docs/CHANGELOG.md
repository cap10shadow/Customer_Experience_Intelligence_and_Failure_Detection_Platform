
# CHANGELOG

All notable engineering changes to the Customer Experience Intelligence & Failure Detection Platform are documented in this file.

The format follows a simplified version of the Keep a Changelog convention.

---

# 2026-08-01

## Phase 9 – Step 2 (Persistence & APIs)

Phase 9 Step 2 has been fully completed, successfully introducing PostgreSQL persistence, read-only REST APIs, and application-level statistics around the frozen Recommendation Domain Engine. The concept of `RecommendationGeneration` was introduced strictly as an execution-grouping and historical auditing persistence mechanism, preventing persistence concerns from polluting the domain.

### Added

- **`RecommendationEntity` & `RecommendationGenerationEntity`** — SQLAlchemy models providing a hybrid relational/JSONB persistence model. Relational columns support rapid filtering/sorting, while JSONB holds unstructured explainability data. Added `action` as a relational column to correct an omission in the frozen architecture and preserve aggregate integrity.
- **`RecommendationRepository`** — cleanly separated repository implementation including atomic `save_many()` operations that commit a full Generation alongside its Recommendations.
- **REST APIs** — strictly read-only endpoints covering `/recommendations`, `/recommendations/latest`, and generation-level lookups. Creation remains explicitly deferred to Step 3.
- **Lightweight DTOs (Summary vs. Full)** — addressed payload bloat by projecting a `RecommendationSummaryResponse` (omitting heavy JSONB) for list views, and a `RecommendationFullResponse` for singular item lookups.
- **`RecommendationStatisticsService`** — application-layer service dynamically aggregating generation-level statistics.
- **Alembic Migration** — automatically tracked database migration for the new tables.

### Verified

- Comprehensive unit, repository, API, and integration testing for all read flows and atomic persistence.
- Verified Full DTO vs. Summary DTO projections correctly strip heavy payloads.
- Verified composite database indexing properly supports the "latest" generation queries.
- Independent principal-engineer-level engineering review performed: the implementation cleanly separates domain logic from infrastructure, handles idempotency modeling well, and strictly follows the frozen architecture (with the documented exception of the `action` column).

---

## Phase 9 – Step 1 (Recommendation Decision Engine)

Phase 9 Step 1 has been fully completed: a pure, deterministic, in-memory domain engine converting completed operational intelligence into explainable Recommendations. No database, repository, REST API, messaging, lifecycle, transaction, or dependency-injection code was introduced -- those are explicitly scoped to Step 2 and Step 3. No existing service was modified.

### Added

- **`IntelligenceContext`** — the engine's single immutable input Domain Value Object, aggregating local, persistence-independent views of Incident, BusinessImpactSummary, RootCauseSummary (optional), NLPIntelligence (optional), and AnomalyIntelligence (optional). `incident`/`business_impact` are required, per the frozen invariant that a Recommendation cannot exist without them.
- **`Recommendation`** — the immutable aggregate (category, action, priority, score, rationale, priority rationale, supporting evidence), with every domain invariant enforced in `__post_init__`.
- **`RecommendationCategory`** (8 values) and **`RecommendationPriority`** (4 tiers) — Domain Enums, preventing free-text classification.
- **`SupportingEvidence`** / **`EvidenceSource`** — structured, weighted, explainable evidence, mirroring Root Cause Service's own `Evidence` pattern.
- **`scoring.py`** — the single, shared Recommendation Scoring Policy every rule and the Consolidator's merge path call into; deliberately no post-processing normalizer, per the ARB's mitigation for cross-rule score inconsistency.
- **`precedence.py`** — the shared Category/Priority precedence policy backing the Consolidator's deterministic ordering (Priority → Category Precedence → Score → Rule Evaluation Order).
- **Eight `RecommendationRule` implementations**, one per category (`EscalationRule`, `MitigationRule`, `SLAProtectionRule`, `InfrastructureActionRule`, `OperationalActionRule`, `CustomerCommunicationRule`, `InvestigateRule`, `MonitorRule`) — independent, deterministic, never calling each other.
- **`RecommendationConsolidator`** — the dedicated Domain Service that deduplicates, merges equivalent recommendations, resolves the one defined conflict (MONITOR vs. a genuinely more urgent category), and applies deterministic ordering. Never fabricates a Recommendation of its own.
- **`RecommendationEngine`** — orchestrates `IntelligenceContext → rules → raw Recommendations → Consolidator → final collection`, entirely in-memory.

### Verified

- 126 new tests added; full `backend` suite (660 tests) passing, no regressions.
- Determinism and immutability verified directly, per component, not just at the engine level.
- Final engineering review performed: no architectural drift, no implementation changes required. One architectural question -- Rules organized by Category vs. by Business Policy -- was raised and resolved in favor of the current design; see `docs/DECISIONS.md` (REC-001).

### Architectural note (reported, not silently resolved)

`root_cause_service` and `business_impact_service` place their rule engines under `app/services/`; `evaluation_service` (and now `recommendation_service`) place theirs under `app/domain/`, per the frozen architecture's explicit Domain-layer vocabulary for every in-scope component. No existing service was modified to reconcile this; the inconsistency between the two older services and the two newer ones is documented here rather than silently copied forward.

---

# 2026-07-28

## Phase 8 – Step 3 (Execution Lifecycle)

Phase 8 Step 3 has been fully completed, introducing the event-driven execution lifecycle around the frozen Step 1/Step 2 engine and persistence layer. No changes were made to the Evaluation engines, `Evaluation` aggregate, or the existing read-only REST API contract.

### Added

- **`EvaluationLifecycleService`** (`application/lifecycle/`) — coordinates the complete execution lifecycle for one inbound `BusinessImpactCompleted` event: execution eligibility, the fast application-level idempotency check, transaction ownership (commit only after successful persistence, rollback on every failure path), invoking `EvaluationOrchestrator`, and publishing `EvaluationCompleted` only after a successful commit.
- **`BusinessImpactCompletedConsumer`** (`infrastructure/messaging/consumers/`) — deserializes the inbound event payload and translates it into the Application-owned `EvaluationExecutionRequest`; performs no validation, repository access, or computation of its own.
- **`InProcessEventPublisher`** (`infrastructure/messaging/publishers/`) — the current, broker-less implementation of the `EventPublisher` port. No message broker (RabbitMQ/Kafka/Redis) exists anywhere in this repository yet; publishing is implemented as a logged, in-process operation behind the same port a real broker adapter would implement later, with zero impact on `EvaluationLifecycleService` or anything above it.
- **`event_id` column on `evaluations`** (new Alembic migration, `a2f5c8e1d3b7`) — nullable, UNIQUE. This is the database-backed correctness guarantee behind the idempotency check: verified under a genuine two-connection concurrent-write test against real PostgreSQL, not just asserted.
- **`EvaluationRepository.save()`** extended (backward-compatible, additive) to accept optional `event_id`/`root_cause_id`/`business_impact_id`, and a new `get_by_event_id()` read operation — closing the lineage gap Step 2 documented as deliberately deferred (`root_cause_id`/`business_impact_id` were always `None` until a future step's event consumer supplied them).
- **`POST /internal/events/business-impact-completed`** — a thin, unversioned internal route standing in for a real broker subscription, exposing the Consumer over HTTP so it is genuinely invocable today.

### Verified

- 123 tests in `evaluation_service` (up from 87), all passing against real PostgreSQL: consumer (success/malformed payload/retryable infrastructure exception/deterministic rejection), lifecycle service (success/duplicate event/validation rejection/orchestrator failure/publisher failure/rollback/unreachable database), orchestrator lineage passthrough, repository UNIQUE-constraint and real concurrent-duplicate protection, and HTTP integration tests for the happy path and every failure scenario.
- Full `backend` test suite: 550 passed, no regressions in any other service.
- Independent architecture-compliance review performed: every layer's Must/Must-Not responsibilities verified by direct code inspection against the frozen Step 3 architecture, with one Clean Architecture finding (Application-layer code referencing a concrete SQLAlchemy type) identified for follow-up.

### Deviations (explicitly reviewed, not silent)

- No message broker exists anywhere in this repository (confirmed by inspection before implementation began: no broker in `docker-compose.yml`, no client library in any service's `requirements.txt`, no shared event-schema module). The Consumer/Publisher are therefore in-process Infrastructure adapters behind Application-owned ports rather than real broker clients — see `docs/DECISIONS.md` (EVAL-001).
- `EvaluationOrchestrator` was extended in place rather than relocated to a new `application/orchestration/` package: it already existed, was already correctly scoped to the frozen Step 3 responsibilities, and relocating it would only churn imports across the existing test suite with no behavioral benefit.

---

# 2026-07-26 / 2026-07-27

## Phase 8 – Step 2 (Persistence & APIs)

Phase 8 Step 2 introduced persistence and read-only REST APIs around the frozen Step 1 Evaluation Engine.

### Added

- `EvaluationRecord` (Domain envelope giving the identity-less Step 1 `Evaluation` aggregate a persisted identity), `EvaluationRepository` port, `PostgreSQLEvaluationRepository`, `EvaluationModel` (JSONB-backed ORM model, `clock_timestamp()`-based ordering, composite index on `incident_id`/`evaluation_version`), and `EvaluationModelMapper`.
- Read-only REST API: `GET /evaluations`, `/evaluations/statistics`, `/evaluations/latest/{incident_id}`, `/evaluations/history/{incident_id}`, `/evaluations/{evaluation_id}` — no write endpoints exist (verified: POST/PUT/PATCH/DELETE all return 405).
- `EvaluationStatisticsService` (Application-layer aggregation, per the frozen decision not to add a repository-level `list_statistics()` method).
- Alembic migration `1185033beadf` (`evaluations` table).

### Verified

- 87 tests passing (added a dedicated multi-page pagination test for `EvaluationStatisticsService.compute()`'s internal scan loop on 2026-07-27, closing the one test-coverage gap identified during engineering review).
- Independent principal-engineer-level implementation review performed: no blocking issues found; DDD/Clean Architecture/Repository Pattern boundaries confirmed correctly held.

---

## Phase 8 – Step 1 (Evaluation Engine)

Phase 8 Step 1 introduced the deterministic Evaluation Engine as a pure, persistence-independent Domain component.

### Added

- `ValidationEngine`, `QualityEngine`, `ExplainabilityEngine`, `ConfidenceAnalyzer`, `EvaluationBuilder`, and the immutable `Evaluation` aggregate (identity-less by design — identity assignment is deliberately a Step 2 persistence-layer concern).
- `EvaluationOrchestrator` (Application layer) coordinating Validation → [Quality Engine ‖ Explainability Engine] → Confidence Analyzer → Evaluation Builder, running the two independent engines concurrently via `asyncio.gather`.
- `CompletedIntelligence` / `DomainEvaluationContext` — plain, persistence-independent input DTOs, deliberately not importing the Root Cause or Business Impact services' own domain/ORM types (DATA-002).

### Verified

- New unit test suite covering every engine and the orchestrator, all passing. Pure in-memory domain logic — no SQLAlchemy, ORM, or persistence involved at this step.

---

# 2026-07-24

## Phase 7 – Step 3 (Business Impact Lifecycle & Validation)

Phase 7 Step 3 has been fully completed. This was a validation-only phase: no changes were made to the Business Impact Engine, its rules, the persistence model, or the REST API contract.

### Added

- **`fakes.py`** — shared, in-memory test-support module (Fake repositories + a realistic, hand-computable synthetic Incident/RootCause scenario builder), used across the new lifecycle test suite.
- **`test_business_impact_lifecycle_e2e.py`** — full lifecycle validation (Incident → Root Cause Summary → Engine → Assessment → Persistence → Repository → DTO), verifying every field against independently hand-computed expectations.
- **`test_api_business_impact_lifecycle.py`** — deeper API integration tests wiring the real Application Service and real Engine through the real FastAPI routes (only the repository layer is Faked), covering creation, retrieval by assessment id, retrieval by incident id (via the existing list filter), list filtering, enum/timestamp serialization, and every documented error path.
- **`test_determinism.py`** — proves identical inputs produce an identical `BusinessImpactAssessment` (scores, severity, priority, explanation) across repeated runs at the engine, application-service, and REST API levels.
- **`test_explainability_contract.py`** — proves the Engine's explanation string is preserved character-for-character through the ORM entity, the response DTO, and full JSON encode/decode, across a quiet, a critical, and a mixed scenario.
- **`backend/services/business_impact_service/README.md`** rewritten to document the verified lifecycle, the actual REST endpoints, what Step 3 verified, and how downstream services should consume this service's data (via a DATA-002 read model, anchored on Incident per ADR-007).

### Verified

- 42 new tests added; 427 / 427 total repository tests passing (385 pre-existing + 42 new).
- mypy clean across all new production and test code.
- Live verification performed against a running PostgreSQL instance (`docker compose up postgres business_impact_service`), using real, already-persisted Incident and Root Cause records from prior pipeline phases: creation, retrieval, list filtering, every documented error path, and determinism across three repeated real requests all confirmed correct. Verification-only rows were removed and containers stopped afterward, leaving the environment as found.
- Zero architectural drift: the Business Impact Engine, Root Cause logic, persistence model, and API/DTO contracts are byte-for-byte unchanged from Phase 7 Step 2.

---

## Architecture Review Board — Documentation Alignment

The Architecture Review Board (ARB) reviewed the platform's complete product vision and long-term architecture, independent of current implementation. Eight architectural decisions were approved and the documentation set was aligned to reflect them.

### Added

- **`docs/ADR_ARCHITECTURE_REVIEW_BOARD.md`** — full ARB session record: purpose, context, review summary, all eight approved decisions, architectural rationale, and long-term vision.
- **`docs/DECISIONS.md`** — eight new ADR entries (ARB-001 through ARB-008) recorded in the permanent decision ledger.

### Changed

- **Terminology aligned:** "Business Risk" → "Business Impact" across `PROJECT_BRAIN.md` and `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md`.
- **Platform identity clarified** (ADR-001) in `PROJECT_BRAIN.md`, `PRD.md`, `ARCHITECTURE.md`, and `README.md`.
- **Long-term intelligence lifecycle vision** (ADR-002, ADR-005) added to `PROJECT_BRAIN.md`, `ARCHITECTURE.md`, `ROADMAP.md`, and `README.md`, explicitly marked as post-MVP and non-binding on the current roadmap.
- **Business Impact Engine framing corrected** (ADR-003) in `PRD.md` and `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md` to reflect the actual five-dimension, generic, deterministic engine rather than legacy scalar risk-score language.
- **Presentation Layer clarified** (ADR-004) in `ARCHITECTURE.md`, `PRD.md`, and `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md`: dashboard/copilot adapt explanation, never the engine.
- **Evidence chain** named conceptually (ADR-006) in `PROJECT_BRAIN.md` and `ARCHITECTURE.md`.
- **Incident's role as the central lifecycle object clarified** (ADR-007): `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md`'s Root Cause Service section was corrected — it previously described a generic `complaint_event_links` ownership that contradicted Root Cause Service's actual, already-implemented consumption of correlated Incidents. `PROJECT_BRAIN.md` and `ARCHITECTURE.md` now name Incident explicitly as this central object.
- **Confidence clarified as stage-specific** (ADR-008) in `ARCHITECTURE.md`, `SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md`, and `DOMAIN_ENUMS_AND_OPERATIONAL_CONSTANTS.md` (new "Confidence Philosophy" section).
- **`docs/PROJECT_STATUS.md`**: added an Architecture Governance section referencing the ARB; corrected a pre-existing internal inconsistency (top status block still read "Step 2 – Ready to Begin" while the rest of the same document already showed Step 2 complete and Step 3 as current focus).

### Verified

- No MVP scope change.
- No completed phase changed.
- No frozen engine (Root Cause Rule Engine, Business Impact Analysis Engine) modified.
- No new service introduced.
- Documents outside the eight ADRs' subject matter (`DATA_MODEL.md`, `DATABASE_SCHEMA_ARCHITECTURE.md`, `ENTITY_MODELING_AND_OWNERSHIP.md`, `CORE_ENTITY_SPECIFICATIONS.md`, `MVP_DATASET_SCOPE.md`, `DATASET_AND_INGESTION_STRATEGY.md`, `REPOSITORY_STRUCTURE.md`) were reviewed and intentionally left unchanged — their content is schema/tooling-level and not addressed by this ARB session.

---

## Phase 7 – Step 2 (Business Impact Persistence & APIs)

Phase 7 Step 2 has been fully completed, introducing the persistence layer and REST APIs for the Business Impact Engine, while strictly maintaining the purity of the deterministic domain engine.

### Added

- **BusinessImpactAssessmentEntity** — SQLAlchemy ORM model representing a persisted impact assessment.
- **Alembic Migration** — database schema changes for `business_impact_assessments`.
- **Repository Layer** — `BusinessImpactRepository` for CRUD operations, plus `IncidentReadRepository` and `RootCauseReadRepository` utilizing service-local read models (`read_models.py`) to respect DATA-002 constraints.
- **Mapper Layer** — `BusinessImpactInputMapper` and `BusinessImpactOutputMapper` that enforce the boundary between persisted ORM entities and the pure domain value objects.
- **Application Service** — `BusinessImpactApplicationService` orchestrating the load -> map -> analyze -> persist -> return workflow without duplicating logic.
- **REST APIs** — Endpoints in `business_impact.py` for creating assessments from an incident ID (`POST /business-impact`) and retrieving them (`GET /business-impact`, `GET /business-impact/{id}`).

### Verified

- API Contract (`POST /business-impact` accepts ONLY `incident_id`).
- Mapper layer strictly performs translation with documented deterministic defaults (`sla_breach_count=0`, `negative_sentiment_ratio=0.0`).
- Repository layer strictly returns persistence/read models.
- Application Service strictly manages orchestration.
- Zero architectural drift detected from the approved Phase 7 Step 2 design.

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

**Phase 7 Step 3 – Business Impact Lifecycle & Validation**

- Validate API endpoints
- Write integration tests for API layer
- Document lifecycle states
