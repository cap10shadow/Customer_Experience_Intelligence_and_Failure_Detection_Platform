# Business Impact Service

**Port:** 8005

Evaluates the business impact of a correlated Incident and its identified Root Cause across five deterministic dimensions -- Financial, Customer, Operational, SLA, and Reputation -- and persists one authoritative, immutable `BusinessImpactAssessment` per analysis run.

The engine (Phase 7 Step 1) is deterministic, explainable, rule-based, and generic: it always evaluates every dimension, never disables one, and never applies organization-specific scoring logic (ADR-003). Persistence and REST APIs (Phase 7 Step 2) sit around the engine without modifying it. Phase 7 Step 3 (this document) validates the complete lifecycle end-to-end and records verified behavior only -- no new functionality is introduced here.

---

## Verified Lifecycle

This is how one Business Impact Assessment is produced, from a client's request down to a persisted database row and back:

```
Client
  │  POST /api/v1/business-impact { "incident_id": "<uuid>" }
  ▼
BusinessImpactApplicationService.create_assessment(incident_id)
  │
  ├─▶ IncidentReadRepository.get_by_id(incident_id)
  │     reads incidents / incident_anomalies / active_anomalies
  │     (owned by the Anomaly Service -- read via a local DATA-002 read model,
  │      never via that service's ORM models)
  │     → PersistedIncident (plain snapshot, includes linked anomalies)
  │
  ├─▶ RootCauseReadRepository.get_by_incident(incident_id)
  │     reads root_causes (owned by the Root Cause Service, same DATA-002 pattern)
  │     → PersistedRootCause (plain snapshot)
  │
  ├─▶ BusinessImpactInputMapper
  │     translates the two snapshots into the Engine's plain, persistence-independent
  │     input value objects -- pure translation, no business logic:
  │       • Incident            (severity, regions, urgency levels)
  │       • RootCauseSummary    (cause, confidence)
  │       • TrendMetrics        (derived from the linked COMPLAINT_SPIKE anomaly)
  │       • AnomalyMetrics      (anomaly types, severity, affected-customer proxy;
  │                              sla_breach_count and negative_sentiment_ratio are
  │                              documented, deterministic defaults of 0 / 0.0 --
  │                              no real data source for these exists yet)
  │
  ├─▶ BusinessImpactEngine.analyze(...)   [frozen, Phase 7 Step 1 -- unmodified]
  │     runs FinancialRule, CustomerRule, OperationalRule, SLARule, ReputationRule
  │     → BusinessImpactProfile → weighting.py → scoring.py → explanation.py
  │     → BusinessImpactAssessment (immutable domain object)
  │
  ├─▶ BusinessImpactOutputMapper.to_orm(incident_id, root_cause_id, assessment)
  │     translates the assessment into a persistable BusinessImpactAssessmentEntity
  │     -- pure translation, no recalculation
  │
  └─▶ BusinessImpactRepository.save(entity)
        INSERTs into business_impact_assessments
        (PostgreSQL populates assessment_id, status=ACTIVE, created_at, updated_at)
  ▼
BusinessImpactAssessmentEntity
  ▼
BusinessImpactAssessmentResponse (Pydantic DTO, `model_validate(..., from_attributes=True)`)
  ▼
JSON response to client
```

Retrieval follows the same repository and DTO layers in reverse, without touching the Engine at all:

- `GET /api/v1/business-impact/{assessment_id}` → `BusinessImpactRepository.get()` → DTO → JSON
- `GET /api/v1/business-impact?incident_id=&severity=&priority=` → `BusinessImpactRepository.list()` → DTO list → JSON

There is no dedicated "get assessments for this incident" endpoint. This is intentional: unlike Root Cause (exactly one record per Incident), an Incident may accumulate multiple immutable Business Impact Assessments over time as it is re-analyzed, so "retrieval by incident id" is served by the existing list endpoint's `incident_id` filter.

**Assessments are immutable.** There is no update endpoint, and none is planned for this service -- re-running analysis for an Incident creates a new, independent assessment row rather than modifying an existing one.

---

## What Phase 7 Step 3 Verified

The full lifecycle above was validated at four levels (see `tests/`):

1. **Lifecycle & end-to-end validation** (`test_business_impact_lifecycle_e2e.py`) -- a realistic synthetic Incident and Root Cause are run through every real component (mapper, engine, output mapper, application service, repository, DTO), and every resulting field is checked against an independently hand-computed expectation -- not just "no exception raised."
2. **API integration** (`test_api_business_impact_lifecycle.py`) -- the real FastAPI routes, real Application Service, and real Engine are exercised over HTTP (only the repository layer's database access is replaced with in-memory Fakes, consistent with this repository's existing testing convention). Covers creation, retrieval by assessment id, retrieval by incident id (via the list filter), list filtering, enum serialization, timestamp serialization, and every documented error path (invalid/missing assessment id, invalid/missing incident id, an incident with no Root Cause yet).
3. **Determinism** (`test_determinism.py`) -- identical inputs are proven to produce an identical `BusinessImpactAssessment` (including scores, severity, priority, and the explanation string) across repeated runs, at the bare engine level, the full application-service level, and over HTTP.
4. **Explainability contract** (`test_explainability_contract.py`) -- the explanation string produced by the Engine is proven to survive, character-for-character, through the ORM entity, the response DTO, and full JSON encode/decode, across a quiet, a critical, and a mixed scenario; each dimension's own reason is independently confirmed present verbatim in the final explanation.

In addition to the automated suite, the full lifecycle above was verified live against a running PostgreSQL instance (`docker compose up postgres business_impact_service`) using real, already-persisted Incident and Root Cause records from prior pipeline phases -- including repeated identical requests (confirming determinism under real infrastructure) and every documented error path.

This is a validation phase only: the Engine, its rules, the persistence model, and the REST contract are exactly as delivered in Phase 7 Step 1 and Step 2.

---

## How Downstream Services Will Consume This

A future service (e.g. the Recommendation Engine) that needs to read Business Impact Assessments must not import this service's ORM model (`BusinessImpactAssessmentEntity`) or domain types directly -- consistent with DATA-002, it should define its own minimal, service-local read model over the `business_impact_assessments` table (the same pattern this service already uses to read `incidents`/`active_anomalies`/`incident_anomalies` and `root_causes`; see `app/repositories/read_models.py`). Incident (per ADR-007) remains the anchor a downstream service should correlate against: a Business Impact Assessment's `incident_id` and `root_cause_id` are the stable foreign keys that thread the full lifecycle -- Anomalies → Root Cause → Business Impact → (future) Recommendation -- together.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/business-impact | Runs Business Impact Analysis for an Incident and persists the result. Body: `{"incident_id": "<uuid>"}`. |
| GET | /api/v1/business-impact/{assessment_id} | Returns a single assessment by its own id. |
| GET | /api/v1/business-impact | Lists assessments, optionally filtered by `severity`, `priority`, and/or `incident_id`. |
| GET | /health | Service health check |

## Local Development

```bash
docker compose up business_impact_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
