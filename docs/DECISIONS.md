
# Architecture Decision Records (ADR)

Project: Customer Experience Intelligence & Failure Detection Platform

## Purpose

This document records significant architectural and engineering decisions made during the development of the platform.

It captures **why** decisions were made, not implementation details. Routine bug fixes, refactoring, and feature additions should be tracked in the changelog instead.

---

## ARCH-001 — Modular Service-Based Architecture

**Status:** Accepted

**Date:** 2026-07-19

### Context

The platform consists of multiple intelligence capabilities including complaint ingestion, NLP enrichment, anomaly detection, root cause analysis, business impact estimation, recommendation generation, and an AI copilot.

### Decision

Adopt a modular service-based architecture within a shared monorepo. Each service owns a specific intelligence responsibility while sharing common infrastructure, utilities, and database patterns.

### Rationale

- Clear separation of concerns.
- Easier independent development and testing.
- Future migration to independently deployable services if required.
- Avoids premature distributed-system complexity.

### Consequences

**Pros**

- High maintainability.
- Clear ownership boundaries.
- Scalable project structure.

**Cons**

- Slight duplication between services.
- Additional coordination required between service interfaces.

---

## ARCH-002 — Shared PostgreSQL Database for MVP

**Status:** Accepted

**Date:** 2026-07-19

### Context

Early MVP development prioritizes engineering simplicity and rapid iteration over distributed persistence.

### Decision

Use a shared PostgreSQL database accessed through SQLAlchemy while maintaining logical service ownership of entities.

### Rationale

- Simplifies development.
- Reduces infrastructure complexity.
- Enables analytics across intelligence stages.
- Supports future migration if required.

### Consequences

**Pros**

- Faster development.
- Easier debugging.
- Simpler deployment.

**Cons**

- Services are logically isolated rather than physically isolated.

---

## ARCH-003 — Service Independence Between Ingestion and NLP

**Status:** Accepted

**Date:** 2026-07-19

### Context

The NLP service enriches complaint records created by the ingestion service.

### Decision

The `ComplaintEnrichment` entity stores only `complaint_id` and does not define an ORM relationship to the `Complaint` model.

### Rationale

- Maintains service independence.
- Prevents SQLAlchemy mapper coupling.
- Simplifies future service separation.

### Consequences

**Pros**

- Cleaner architecture.
- Easier testing.
- Stable mapper initialization.

**Cons**

- Complaint details must be explicitly queried when required.

---

## ARCH-004 — Deterministic NLP for MVP

**Status:** Accepted

**Date:** 2026-07-19

### Context

The roadmap targets explainable operational intelligence before introducing advanced AI models.

### Decision

Implement the initial NLP pipeline using deterministic rules and keyword-based classification instead of machine learning models.

### Rationale

- Fully explainable outputs.
- Faster implementation.
- Easier debugging.
- Stable and reproducible behavior.

### Consequences

**Pros**

- Transparent decision-making.
- No model training required.
- Predictable results.

**Cons**

- Lower linguistic flexibility.
- Less accurate than modern ML models on complex text.

---

## DATA-001 — Database-Level Referential Integrity Across Service Boundaries

**Status:** Accepted

**Date:** 2026-07-19

### Context

The platform adopts a modular architecture where the NLP service needs to enrich complaint records created by the Ingestion service, but without creating tightly coupled ORM models.

### Decision

The `ComplaintEnrichment` entity stores the `complaint_id` without an ORM `ForeignKey`. Referential integrity is enforced strictly by PostgreSQL database migrations, while each service owns only its own ORM models.

### Rationale

- Ensures data integrity without coupling Python model dependencies.
- Services do not have to share SQLAlchemy mappers.
- Facilitates future decoupling into separate databases if needed.

### Consequences

**Pros**

- Database-level safety.
- Decoupled ORM definitions.
- True service independence while maintaining data integrity.

**Cons**

- Requires careful management of raw database migrations.
- SQLAlchemy cannot automatically traverse relationships via `.complaint`.

---

## DATA-002 — Service-Local Read Models

**Status:** Accepted

**Date:** 2026-07-19

### Problem

Some services legitimately need to read data owned by another service — for example, the Anomaly Service's Trend Engine must read `complaints` and `complaint_enrichments`, owned by the Ingestion and NLP services respectively. Importing another service's SQLAlchemy ORM model class to do this reintroduces the same class of problem seen in Phase 4: SQLAlchemy mapper/metadata coupling, fragile startup behavior, and a hard Python-level dependency between services that are supposed to remain independently deployable.

### Decision

- Backend services must never import ORM models owned by another service.
- Each service defines its own minimal SQLAlchemy Core read models when direct database access to another service's tables is required.
- Read models exist only for querying already-persisted, shared data — they are not used for writes and carry no business logic.
- Business ownership of an entity (schema, migrations, write access) remains exclusively within the owning service, regardless of how many other services read from it.

### Rationale

- Prevents SQLAlchemy metadata coupling between services — the root cause of the Phase 4 mapper-initialization failure.
- Preserves service autonomy: any service can be developed, tested, and deployed without importing another service's Python package.
- Keeps read access explicit and minimal — a service declares exactly the columns it needs, nothing more.
- Generalizes the precedent set by ARCH-003 and DATA-001 (the NLP/Complaint relationship removal) into a platform-wide engineering standard rather than a one-off fix.

### Consequences

**Pros**

- No cross-service ORM class imports, ever.
- Each service's mapper configuration is fully self-contained and cannot be broken by another service's schema changes.
- Read models are cheap to write and easy to audit — a handful of `Column` declarations on a dedicated `MetaData` instance.

**Cons**

- Column definitions for a shared table may be duplicated, in reduced form, across every service that reads it.
- If the owning service changes a column's type or name, every dependent service's read model must be updated manually — there is no shared source of truth beyond the migration history.

---

## ANOMALY-001 — Hybrid Anomaly Lifecycle Management

**Status:** Accepted

**Date:** 2026-07-20

### Problem

The Anomaly Detection Engine needs a persistence strategy to store detected anomalies. Pure snapshot persistence (storing every anomaly on every run) leads to unbounded database growth and massive duplication, creating performance bottlenecks for simple dashboard queries. Conversely, latest-state-only persistence (overwriting existing anomalies) destroys the timeline, making future Root Cause Analysis (RCA) and Business Impact Analysis impossible.

### Alternatives Considered

1. **Pure Snapshot Persistence (Event Sourcing):** Create a new record for every detected anomaly during every run. (Rejected due to database bloat and slow querying for current state).
2. **Latest-State-Only Persistence (CRUD):** Update the anomaly in place, losing historical progression. (Rejected due to inability to support RCA and Explainability).
3. **Hybrid Approach:** Maintain an active state table for fast operational querying and an append-only timeline table for state changes. (Chosen).

### Decision

Implement a hybrid persistence architecture using two tables:
- `active_anomalies`: A mutable table representing the current state of ongoing issues (fast operational lookups).
- `anomaly_history`: An append-only ledger tracking lifecycle state changes (e.g., detection, severity updates, resolution) for historical RCA.

### Rationale

This approach provides O(1) operational dashboarding by querying only the active anomalies, while perfectly preserving the timeline context required by the future AI Copilot and Root Cause engines without storing redundant data. 

### Consequences

**Pros**
- Zero data bloat (snapshots are only created on state changes).
- Fast UI rendering (Dashboard only queries `active_anomalies`).
- Full auditability and perfect RCA integration (Timeline is preserved in `anomaly_history`).

**Cons**
- Requires more complex persistence logic to calculate state deltas during the detection run.

### Anomaly Lifecycle State Machine

The following diagram illustrates the anomaly lifecycle:

```mermaid
stateDiagram-v2
    [*] --> Detected
    Detected --> Active
    Active --> Updated
    Updated --> Active
    Active --> Resolved
    Resolved --> Reactivated
    Reactivated --> Active
    Resolved --> [*]
```

### Execution Flow

The sequence of the hybrid persistence model during a detection run:

```mermaid
sequenceDiagram
    participant Client
    participant API as Anomaly API
    participant Engine as Anomaly Engine
    participant DB as Database (active & history)
    
    Client->>API: POST /anomalies/run
    API->>Engine: trigger_detection()
    Engine->>Engine: calculate_trends()
    Engine->>Engine: evaluate_rules()
    Engine->>Engine: generate_fingerprints()
    Engine->>DB: query active_anomalies by fingerprint
    alt New Anomaly
        Engine->>DB: INSERT into active_anomalies
        Engine->>DB: INSERT into anomaly_history (DETECTED)
    else Existing Anomaly (Severity Changed)
        Engine->>DB: UPDATE active_anomalies
        Engine->>DB: INSERT into anomaly_history (UPDATED)
    else Existing Anomaly (Unchanged)
        Engine->>DB: UPDATE active_anomalies (last_seen_at)
    else Resolved Anomaly
        Engine->>DB: UPDATE active_anomalies (status=Resolved)
        Engine->>DB: INSERT into anomaly_history (RESOLVED)
    end
    Engine-->>API: return detection results
    API-->>Client: 200 OK (Run Summary)
```

---

## ANOMALY-002 — Fingerprint-Based Anomaly Identity

**Status:** Accepted

**Date:** 2026-07-20

### Purpose of Fingerprints

To reliably match a newly detected anomaly from the current run against an existing active anomaly in the database, the system requires a deterministic, stable identifier.

### Decision

Implement a stable anomaly identity using a deterministic SHA-256 hash (fingerprint) of the anomaly's core dimensions (e.g., `detector_type`, `dimension_value`). 

### Rationale

- **Stable Anomaly Identity:** An anomaly maintains the exact same ID across multiple engine executions as long as the underlying dimensional issue persists.
- **Duplicate Prevention:** The database enforces a unique constraint on the fingerprint for active anomalies, guaranteeing that the same issue is never double-counted.
- **Reactivation Behavior:** If a previously resolved anomaly resurfaces with the same fingerprint, it can be seamlessly reactivated and linked to its historical timeline.
- **Future Extensibility:** The fingerprinting logic is centralized. If new dimensions are added in the future, the hashing algorithm can be versioned to prevent breaking existing historical fingerprints.

---

## INCIDENT-001 — Incident-Centric Correlation Model

**Status:** Accepted

**Date:** 2026-07-20

### Problem

As the Anomaly Detection Engine scales, it will detect multiple related anomalies across different dimensions (e.g., a spike in "Login Failures" and a spike in "Authentication Errors" in the same region at the same time). If these individual anomalies are fed directly into the future Root Cause Analysis engine, it will create redundant RCA workflows and noise.

### Alternatives Considered

1. **Direct Anomaly RCA:** Send every anomaly independently to the Root Cause Engine. (Rejected due to noise and redundant causal evaluations).
2. **Incident-Centric Correlation (Chosen):** Introduce a logical grouping layer (Incident Correlation) at the end of Phase 5. This engine evaluates active anomalies and clusters related ones into unified "Incidents". 

### Decision

Implement an Incident Correlation Engine as the final step of Phase 5. This engine serves as the transition point between detection and causation. Anomalies are grouped into Incidents based on temporal, regional, and categorical proximity. The Root Cause Engine (Phase 6) will investigate *Incidents*, not individual anomalies.

### Rationale

- **Noise Reduction:** Operators and AI Copilots receive a unified incident report rather than dozens of redundant anomaly alerts.
- **Clearer Causation:** Investigating a cluster of related anomalies provides a stronger signal for the Root Cause Engine than investigating them in isolation.
- **Separation of Concerns:** Phase 5 is fully responsible for "What is happening?" (Trend -> Anomaly -> Incident), leaving Phase 6 entirely focused on "Why is it happening?" (Root Cause).

### Consequences

**Pros**
- Cleaner RCA architecture.
- Better operational dashboarding (focusing on Incidents rather than noisy anomalies).
- Highly structured data model preparing for Phase 6.

**Cons**
- Requires correlation logic and an additional schema entity (`Incident`) to track the groups.

---

## RCA-001 — Persistence-Independent Domain Input Model

**Status:** Accepted

**Date:** 2026-07-21

### Context

Root Cause Analysis (Phase 6) must consume `Incidents` generated by the Incident Correlation Engine (Phase 5). Importing Incident ORM models from the Anomaly Service into the Root Cause Service violates DATA-002 (Service-Local Read Models) and creates tight cross-service coupling.

### Decision

Introduce a persistence-independent `Incident` domain model (`domain/incident.py`) dedicated purely to Root Cause inference. This is a plain, immutable dataclass containing only the information required for rule evaluation.

### Rationale

- **Service Independence:** The Root Cause Engine does not depend on the internal database schema or ORM models of another service.
- **No ORM Coupling:** Avoids SQLAlchemy mapper initialization issues and dependency leakage.
- **Pure Domain Logic:** Keeps the Root Cause Engine purely functional, deterministic, and isolated.
- **Easier Testing:** The engine can be tested with plain dataclasses without requiring a database session.
- **Future Portability:** A completely isolated domain engine can be easily moved or scaled if needed.

### Consequences

**Pros**
- Fully isolated domain engine.
- Independent, fast, database-less unit testing.
- No SQLAlchemy dependencies inside the engine logic.
- Stable, predictable architecture.

**Cons**
- Requires mapping from persisted Incident entities in Step 2 before passing them into the engine.
- Small duplication of field definitions (Incident attributes exist in both the Phase 5 ORM and Phase 6 Domain).

---

## BI-001 — Business Impact Uses Deterministic Rules

**Status:** Accepted

**Date:** 2026-07-22

### Context

Phase 7 Step 1 must evaluate the business consequences of an Incident and its identified Root Cause. The platform's core principle is explainability-first: every output consumed by the AI Copilot must be fully auditable and reproducible without dependency on probabilistic models.

### Decision

The Business Impact Analysis Engine evaluates all five impact dimensions (Financial, Customer, Operational, SLA, Reputation) using deterministic, threshold-based rules. No machine learning, probabilistic scoring, or AI inference is used.

### Rationale

- **Explainability:** Every impact level can be traced to the exact rule condition and input value that triggered it.
- **Auditability:** Outputs are fully reproducible for any given set of inputs, enabling reliable regression testing.
- **Reliability:** Deterministic rules do not degrade over time or require retraining.
- **AI-Safe:** The AI Copilot downstream can safely consume the output knowing it was produced by auditable, transparent logic.

### Consequences

**Pros**
- Fully explainable and auditable impact assessments.
- Predictable, reproducible behavior across all environments.
- No model training, deployment, or versioning overhead.

**Cons**
- Rule thresholds require manual review and tuning as business conditions evolve.

---

## BI-002 — Independent ImpactRule Abstraction

**Status:** Accepted

**Date:** 2026-07-22

### Context

The Business Impact Engine must evaluate five distinct business dimensions. Each dimension has independent logic, thresholds, and escalation conditions. Coupling dimension logic within a single class or function would violate the Single Responsibility Principle and make isolated testing impossible.

### Decision

Define an `ImpactRule` abstract base class in the domain layer. Each of the five business dimensions is implemented as an independent, concrete rule class that implements this interface. No rule has knowledge of any other rule.

### Rationale

- **Single Responsibility:** Each rule class owns exactly one dimension's evaluation logic.
- **Isolated Testing:** Every rule can be unit-tested independently with no dependency on the engine or other rules.
- **Clarity:** The boundary between evaluation logic (rules) and orchestration logic (engine) is explicit.

### Consequences

**Pros**
- Independent development and testing of each dimension's rule.
- Adding a new rule requires no changes to existing rules.
- Rule logic is self-contained and easily reviewable.

**Cons**
- Requires a small number of parallel rule class definitions rather than a single conditional block.

---

## BI-003 — BusinessImpactEngine Orchestrates Injected ImpactRule Implementations

**Status:** Accepted

**Date:** 2026-07-22

### Context

The Business Impact Engine needs to coordinate the evaluation of all five business dimensions and assemble the final `BusinessImpactAssessment`. The engine must remain open for extension (new rules) without requiring modification, and must depend on the abstraction rather than concrete rule implementations.

### Decision

`BusinessImpactEngine` accepts a `Sequence[ImpactRule]` at construction time. It iterates over the injected rules, dispatches each evaluation, assembles the `BusinessImpactProfile`, and delegates to `scoring.py`, `weighting.py`, and `explanation.py` for the final assessment. A `default_rules()` factory in the same module provides the standard five-rule configuration.

### Rationale

- **Dependency Inversion:** The engine depends on the `ImpactRule` abstraction, never on concrete rule classes.
- **Open/Closed:** New rules can be injected without modifying the engine.
- **Testability:** The engine can be tested with any mock or stub implementation of `ImpactRule`.
- **Explicit Configuration:** The `default_rules()` factory makes the standard configuration discoverable without hiding it inside the engine constructor.

### Consequences

**Pros**
- Engine logic is completely decoupled from individual rule implementations.
- Rule composition is explicit and injectable.
- Future rule additions require zero engine changes.

**Cons**
- The caller is responsible for assembling the rule sequence (mitigated by the `default_rules()` factory).

---

## BI-004 — ImpactEvaluation Carries Deterministic Reasoning

**Status:** Accepted

**Date:** 2026-07-22

### Context

The explanation engine must generate deterministic, human-readable explanations for each dimension's impact level. If rules return only an `ImpactLevel` enum value, the explanation engine would need to duplicate rule logic to reconstruct why that level was reached — creating hidden coupling and violating the Single Responsibility Principle.

### Decision

Each `ImpactRule` returns an `ImpactEvaluation` value object containing the dimension, the level, and a pre-computed deterministic reason string. The explanation engine aggregates these reason strings without applying any additional business logic.

### Rationale

- **No Duplicated Logic:** The explanation engine never re-evaluates thresholds or conditions; it only aggregates pre-computed reasons.
- **Single Responsibility:** Each rule owns both the classification decision and its corresponding explanation.
- **Auditability:** Every reason string is deterministically generated at the point of rule evaluation, tied directly to the specific condition that fired.

### Consequences

**Pros**
- Explanation engine is a pure aggregator with no business logic.
- No hidden coupling between explanation generation and rule evaluation.
- Explanation output is fully traceable to the rule that produced it.

**Cons**
- Each rule must produce both a level and a reason string, slightly increasing rule complexity.

---

## BI-005 — BusinessImpactProfile Separates Evaluation from Final Assessment

**Status:** Accepted

**Date:** 2026-07-22

### Context

The Business Impact Engine produces five independent `ImpactEvaluation` results. These evaluations must be aggregated into a weighted business score, an overall severity classification, a priority level, a confidence score, and a final explanation before producing the output domain object. Combining all of this logic into a single step would produce an opaque, untestable transformation.

### Decision

Introduce `BusinessImpactProfile` as an intermediate value object that holds all five named `ImpactEvaluation` fields and provides an `all_evaluations()` helper. The engine passes the profile to `scoring.py`, `weighting.py`, and `explanation.py` independently before assembling the final `BusinessImpactAssessment`.

### Rationale

- **Separation of Responsibilities:** Profile assembly, score computation, and assessment construction are three distinct, independently testable steps.
- **Clarity:** The profile makes the intermediate state explicit rather than passing five separate arguments through multiple functions.
- **Testability:** Each transformation step (weighting, scoring, explanation) can be tested against a constructed `BusinessImpactProfile` without invoking the full engine pipeline.

### Consequences

**Pros**
- Clear intermediate representation of aggregated evaluation results.
- Independent testability of scoring, weighting, and explanation logic.
- Reduces argument count across internal engine functions.

**Cons**
- Introduces one additional domain object that does not appear in the final API output.

---

## BI-006 — Business Impact Service Owns Local Domain Input Models

**Status:** Accepted

**Date:** 2026-07-22

### Context

The Business Impact Engine requires structured input representing an Incident, a Root Cause Summary, Trend Metrics, and Anomaly Metrics. These domain concepts are owned by the Anomaly Service (Phase 5) and the Root Cause Service (Phase 6). Importing ORM models or domain classes from those services into the Business Impact Service would violate DATA-002 (Service-Local Read Models) and create tight cross-service coupling.

### Decision

Introduce four local, persistence-independent value objects within the Business Impact Service: `Incident`, `RootCauseSummary`, `TrendMetrics`, and `AnomalyMetrics`. These are plain, immutable dataclasses containing only the fields required for impact evaluation. They follow the same pattern established by RCA-001 (Persistence-Independent Domain Input Model) in Phase 6.

### Rationale

- **Service Independence:** The Business Impact Engine does not depend on ORM models or domain classes from Phase 5 or Phase 6 services.
- **No ORM Coupling:** The engine remains a pure, persistence-free domain component with no SQLAlchemy dependencies.
- **Consistency:** Follows the service-isolation convention already established and proven in Phase 6 (RCA-001).
- **Testability:** The engine can be fully tested using plain dataclass instances with no database or service dependencies.

### Consequences

**Pros**
- Fully isolated domain engine.
- No cross-service Python-level imports.
- Independent, database-less unit testing.
- Stable architecture regardless of upstream service schema changes.

**Cons**
- Requires a mapper in Phase 7 Step 2 to translate persisted ORM records into these plain input value objects before passing them to the engine.
- Small duplication of field definitions across service boundaries (mitigated by the minimal, purpose-scoped nature of each input model).

---

## ARB-001 — Platform Identity

**Status:** Accepted

**Date:** 2026-07-24

### Context

The platform's identity was described consistently in spirit across every document but had never been given a single, formal, citable name — leading to informal variation ("operational intelligence platform," "complaint analytics platform") in casual references.

### Decision

The platform is formally named the Customer Experience Intelligence & Operational Decision Support Platform. Its purpose is to transform customer complaints into explainable operational intelligence and evidence-based business decisions. The platform is NOT merely a complaint analytics dashboard.

### Rationale

- Gives a name to an identity that was already implicit in the product's non-goals and positioning.
- Prevents future documentation or onboarding material from drifting toward a "dashboard" framing the platform has always explicitly rejected.

### Consequences

**Pros**
- Consistent, citable identity across all documentation.

**Cons**
- None — purely a naming/documentation clarification.

---

## ARB-002 — Intelligence Lifecycle

**Status:** Accepted (long-term vision; not an MVP commitment)

**Date:** 2026-07-24

### Context

The documented intelligence pipeline (Complaint → NLP → Anomaly → Incident → Root Cause → Business Impact → Recommendation → Dashboard/Copilot) is a one-way flow. Nothing that happens after a recommendation is delivered ever flows back into the platform's intelligence.

### Decision

The platform's long-term architectural vision extends the pipeline into a complete lifecycle: Complaint → NLP → Anomaly → Incident → Root Cause → Business Impact → Recommendation → Human Action → Outcome → Organizational Knowledge → Continuous Improvement → AI Copilot. This is a long-term vision. It is explicitly NOT part of the MVP and does not change any current phase, deliverable, or roadmap commitment.

### Rationale

- Without capturing what happened after a recommendation, confidence scores and severity bands can never be validated against reality.
- Naming the destination now allows current phases to be built in a way that does not foreclose it later, without requiring any current work to change.

### Consequences

**Pros**
- Gives the roadmap an explicit long-term destination.
- Does not obligate any current phase to change.

**Cons**
- Introduces conceptual scope (Human Action, Outcome, Organizational Knowledge) that is not yet scheduled on the roadmap.

---

## ARB-003 — Business Impact Engine Remains Generic

**Status:** Accepted

**Date:** 2026-07-24

### Context

The platform is positioned for multiple industries (e-commerce, logistics, fintech, SaaS, telecom, marketplaces, subscription services) that define business impact differently, creating pressure for the Business Impact Engine to branch its scoring logic per organization.

### Decision

The Business Impact Engine remains deterministic, explainable, rule-based, and generic. It always evaluates every Business Impact dimension (Financial, Customer, Operational, SLA, Reputation). No dimensions are disabled. No organization-specific scoring logic is introduced. The engine produces one authoritative Business Impact Assessment. This reaffirms and reinforces BI-001 through BI-006 without altering their content.

### Rationale

- Preserves the engine's determinism, testability, and auditability established in BI-001 through BI-006.
- Organization-specific emphasis is handled at the Presentation Layer (ARB-004), not inside the engine, keeping the engine reusable and stable across every future industry vertical.

### Consequences

**Pros**
- The engine remains stable, generic, and reusable across organizations.
- Prevents scoring logic from fragmenting per customer.

**Cons**
- Organization-specific prioritization must be solved entirely at the presentation layer for now; a future, explicitly-designed configuration layer would be required if per-organization weighting is ever needed inside the engine itself. No such layer is introduced by this decision.

---

## ARB-004 — Presentation Layer Adapts Explanation, Not the Engine

**Status:** Accepted

**Date:** 2026-07-24

### Context

Different personas (Executive, Business Analyst, Reliability Engineer, Operations Manager) and different organizations legitimately care about different Business Impact dimensions for the same incident.

### Decision

Rather than changing Business Impact calculations, the Presentation Layer (Dashboard and AI Copilot) allows users to explore specific dimensions, compare dimensions, and request business-specific explanations. The Presentation Layer adapts the explanation, not the engine. Business reasoning remains consistent for every organization and every user.

### Rationale

- Keeps the engine (ARB-003) generic and universal while still letting different audiences focus on what matters to them.
- Ensures the same incident produces the same authoritative assessment regardless of who is viewing it — only the narration and framing differ.

### Consequences

**Pros**
- Full flexibility of exploration and explanation without compromising engine determinism.

**Cons**
- Presentation Layer must be designed to filter/compare/re-narrate an already-computed assessment rather than requesting a recomputation — a constraint future dashboard/copilot design must respect.

---

## ARB-005 — Organizational Knowledge

**Status:** Accepted (long-term vision; not an MVP commitment)

**Date:** 2026-07-24

### Context

Every anomaly, root cause, and impact assessment is currently evaluated as if it were the first of its kind; the platform has no memory of recurring patterns or prior responses.

### Decision

The platform should preserve organizational knowledge. Future phases should support learning from Human Actions, Outcomes, Historical Incidents, and Previous Recommendations, enabling continuous organizational learning. This is long-term vision only; no current phase, entity, or persisted schema is affected.

### Rationale

- Provides the substantive content behind the "Organizational Knowledge" and "Continuous Improvement" stages of ARB-002's lifecycle.
- Names a destination without prescribing implementation, preserving full design freedom for whichever future phase takes this on.

### Consequences

**Pros**
- Establishes long-term direction for future roadmap planning.

**Cons**
- No mechanism, schema, or phase is defined yet — intentionally deferred.

---

## ARB-006 — Evidence Chain (Conceptual)

**Status:** Accepted

**Date:** 2026-07-24

### Context

Each intelligence stage already produces its own explainable output (NLP enrichment fields, anomaly explanations, Root Cause `Evidence` objects, Business Impact `ImpactEvaluation` reasons) independently, with no document naming these as segments of one continuous story.

### Decision

Every intelligence stage contributes evidence. The platform should conceptually maintain a connected evidence chain across Complaint → NLP → Anomaly → Incident → Root Cause → Business Impact → Recommendation. This is a conceptual architecture decision, not an implementation requirement.

### Rationale

- Names a principle that already exists in practice, guiding future explainability and AI-copilot work toward treating the chain as one evidentiary narrative.
- Explicitly does not require a shared schema or new service, preserving every service's autonomy over its own explanation format (consistent with DATA-002).

### Consequences

**Pros**
- Gives future explainability/RAG work a documented principle to build toward.

**Cons**
- None — no implementation change is required or introduced.

---

## ARB-007 — Incident as the Central Lifecycle Object

**Status:** Accepted

**Date:** 2026-07-24

### Context

Some documentation (e.g. SERVICE_RESPONSIBILITY_AND_PERSISTENCE_ARCHITECTURE.md, prior to this session) described Root Cause correlation in terms of a generic complaint-event link, distinct from the Incident entity already established by INCIDENT-001 and consumed by Root Cause Analysis per RCA-001. This created a risk of introducing a duplicate "Case"-like concept.

### Decision

A separate "Case" entity will NOT be introduced. Instead, Incident naturally evolves into the central lifecycle object connecting Anomalies → Root Cause → Business Impact → Recommendation → Human Action → Outcome → Organizational Knowledge.

### Rationale

- Incident already plays this role in practice (INCIDENT-001, RCA-001); introducing a parallel "Case" concept would duplicate an existing entity.
- Gives every future stage (Recommendation, Human Action, Outcome, Organizational Knowledge) a single, existing anchor object to attach to.

### Consequences

**Pros**
- No duplicate entity; Incident's existing central role is simply made explicit.
- Every future lifecycle extension has a clear, already-implemented attachment point.

**Cons**
- Documentation describing Root Cause correlation in terms other than "consumes Incidents" (see this session's documentation alignment) required correction to remove the contradiction.

---

## ARB-008 — Confidence Remains Stage-Specific

**Status:** Accepted

**Date:** 2026-07-24

### Context

"Confidence" is produced by multiple stages (NLP classification, anomaly severity, Root Cause `confidence_score`/`confidence_level`, Business Impact `confidence`) with materially different meanings, previously undocumented as intentional.

### Decision

Confidence remains stage-specific. Each service owns its own confidence definition. The architecture clarifies this explicitly. It does NOT force one universal confidence score.

### Rationale

- Root Cause's confidence measures certainty that the correct deterministic rule fired; Business Impact's confidence measures completeness of available input data. These are not interchangeable and should not be forced onto one scale.
- Documenting this as intentional prevents a future, well-intentioned "unification" effort from destroying meaningful, stage-specific signal.

### Consequences

**Pros**
- Prevents loss of meaning from forcing dissimilar concepts onto one scale.
- Gives future engineers a clear, documented reason not to "fix" this into a single universal score.

**Cons**
- A future Copilot or dashboard summarizing "confidence" across stages must present it per-stage rather than as one number — an explicit design constraint, not a defect.

---

## EVAL-001 — In-Process Event Consumer/Publisher Pending a Real Message Broker

**Status:** Accepted

**Date:** 2026-07-28

### Context

Phase 8 Step 3's frozen architecture requires an Infrastructure Event Consumer receiving `BusinessImpactCompleted` events and an Infrastructure Event Publisher emitting `EvaluationCompleted` events. Before implementation began, the platform was inspected for existing messaging infrastructure: no message broker (RabbitMQ, Kafka, Redis, or otherwise) exists anywhere in this repository — not in `docker-compose.yml`, not in any service's `requirements.txt`, not in `backend/shared/`. No service publishes any event today; `business_impact_service`'s own `create_assessment()` flow ends at its repository's `save()` with no event emission. The frozen architecture specifies consumer/publisher *responsibilities* but never mandates a specific transport technology, and introducing one (a broker, new `docker-compose` service, cross-service wiring into `business_impact_service`) would be a scope decision beyond implementing the frozen design, and would require modifying an already-completed, out-of-scope service.

### Decision

Implement the Event Consumer (`BusinessImpactCompletedConsumer`) and Event Publisher (`InProcessEventPublisher`) as Infrastructure adapters behind Application-owned ports (`EventPublisher`), backed by an in-process implementation: the Consumer is exposed via a thin internal HTTP route (`POST /internal/events/business-impact-completed`) rather than a real broker subscription, and the Publisher records outbound events via the standard logger rather than a real broker client. `EvaluationLifecycleService` and everything above it depends only on the abstract `EventPublisher` port and never on a concrete transport.

### Rationale

- The frozen architecture's own Publisher Behaviour section already treats this platform as prototype-stage (explicitly rejecting the Outbox Pattern for the same reason), making an in-process stand-in a consistent, not exceptional, choice.
- Keeping the Consumer/Publisher behind Application-owned ports (the same Dependency Inversion pattern already established for `EvaluationRepository`) means introducing a real broker later is a pure Infrastructure-layer change — a new adapter implementing the same `EventPublisher` port, wired in at the same composition root (`presentation/dependencies.py`) — with zero impact on `EvaluationLifecycleService`, `EvaluationOrchestrator`, or the Domain.
- Avoids silently introducing new platform-wide infrastructure (a broker choice, new deployment dependency, new service-to-service wiring) as a side effect of implementing one service's execution lifecycle.

### Consequences

**Pros**
- Phase 8 Step 3 is fully implementable and independently verifiable today, with no dependency on infrastructure that doesn't yet exist.
- The eventual real-broker migration is isolated to Infrastructure: no Application/Domain code changes required.

**Cons**
- `business_impact_service` does not yet actually emit a `BusinessImpactCompleted` event — nothing in the platform will invoke this pipeline in production until a real event source and transport exist. The internal HTTP route is a deliberate, documented stand-in, not a production trigger.
- Whichever broker technology is eventually chosen (and the accompanying `business_impact_service` change to actually publish) remains an open decision for a future phase.

---

## REC-001 — Recommendation Rules Are Organized One Rule Per Recommendation Category

**Status:** Accepted

**Date:** 2026-08-01

### Context

During Phase 9 Step 1's final engineering review, an alternative rule-organization scheme was raised: instead of one `RecommendationRule` per `RecommendationCategory` (e.g. `EscalationRule` producing only `ESCALATE`), organize rules around business policies (e.g. a single `SLAProtectionRule` internally deciding to emit `ESCALATE`, `CUSTOMER_COMMUNICATION`, and increased monitoring together, whenever SLA risk is detected). The question was whether this Business-Policy shape would better reflect how a stakeholder actually describes the domain ("our SLA policy is to escalate, notify the customer, and monitor more closely").

### Decision

Keep the current one-rule-per-category design. Each `RecommendationRule` owns exactly one `RecommendationCategory` and never emits any other. When one underlying business signal genuinely warrants multiple categories of response, that emerges from multiple independent rules each firing on their own criteria against the same shared `IntelligenceContext` — not from one rule internally bundling several categories together.

### Rationale

- **The "one signal, multiple actions" need is already met** by the existing pipeline (`IntelligenceContext -> independent rules -> raw Recommendations -> Consolidator`), without a Business-Policy rule shape: if SLA risk is severe enough, `SLAProtectionRule` fires for `SLA_PROTECTION`, and if the same underlying severity also crosses `EscalationRule`'s and `CustomerCommunicationRule`'s own independent thresholds, they fire too — the "cascade" a Business Policy would hand-code is instead an emergent property of several small, focused rules sharing one input. The question's own example is achievable today without any code change.
- **Open/Closed Principle**: category-per-rule is strictly more open/closed. Adding a brand-new, independent category is a pure addition (one new file, one new enum value, one new line in `default_rules()`) with zero modification to any existing rule. Under a Business-Policy scheme, making an existing policy also cover a new category requires modifying that policy's internal branching — a direct OCP violation the current design avoids by construction.
- **Clean separation of pipeline stages**: the frozen architecture deliberately splits "detection" (Rules) from "cross-cutting resolution" (`RecommendationConsolidator` — dedup, merge, conflict resolution, ordering). A policy rule that internally decides "these categories belong together" would be making a consolidation-level decision inside a rule, blurring a boundary the architecture drew on purpose.
- **DDD consistency across the platform**: this repeats the exact decomposition principle already used by `root_cause_service` (one `Rule` per `RootCause`) and `business_impact_service` (one `ImpactRule` per `ImpactDimension`) — the service's primary Domain classification enum is always the unit of rule decomposition. `RecommendationCategory` is explicitly a Domain Enum in the frozen architecture; treating it with the same seriousness maintains a platform-wide convention, not just local consistency.
- **Human Action phase compatibility** (ADR-002's long-term `Recommendation -> Human Action -> Outcome` lifecycle): each `Recommendation` already carries exactly one category and is independently addressable. A future Human Action tracker will want to record disposition (actioned / dismissed / pending) per Recommendation. Category-per-rule naturally produces independently-actionable records; a policy rule bundling several categories into "one response" would still need to emit them as separate `Recommendation` objects to support this — at which point it is functionally identical to several independent category-rules, just relocated into fewer, larger files.
- **Maintainability**: eight small (~60-90 line), independently testable rule files versus fewer, larger policy files with more internal branching and more test-case combinations per file — directly serving the frozen architecture's own instruction to "prefer small composable classes over monolithic implementations."

### Consequences

**Pros**
- Every category is independently addable, testable, and (later) actionable without touching existing rules.
- Matches the platform-wide precedent (Root Cause, Business Impact) of decomposing rules by the service's primary Domain enum.
- Keeps rule-level detection and Consolidator-level resolution as two genuinely distinct responsibilities.

**Cons**
- Minor duplication of threshold tuples (e.g. `("high", "critical")`) across a handful of rule files that each independently check a different `BusinessImpactSummary` dimension — flagged as a non-blocking, low-value "Can Improve Later" item in the Phase 9 Step 1 final review, not a consequence of this decision specifically.
- If a future category genuinely requires reasoning that cannot be decomposed per-category without real logic duplication (not just a repeated constant), this decision should be revisited then — not preemptively redesigned now against a hypothetical.

---

## REC-002 — Persistence of Recommendation Action Field

**Status:** Accepted

**Date:** 2026-08-01

### Context

During Phase 9 Step 2 implementation, an omission in the frozen architecture was discovered. The frozen persistence specification omitted the `action` field from both relational and JSONB column definitions. However, `action` is a mandatory domain field enforced by the `Recommendation` aggregate's `__post_init__` method.

### Decision

Introduce `action` as a relational column in the `RecommendationEntity` ORM model.

### Rationale

- **Aggregate Integrity:** To satisfy the repository pattern's contract, whatever goes into `save_many()` must be perfectly restorable by `list_by_incident()`. Dropping `action` violates this contract, as the aggregate cannot be reconstructed without it.
- **Clean Architecture:** Adding the column to the ORM model aligns the Infrastructure layer with the Domain layer's reality. It does not leak persistence into the domain; rather, it ensures persistence faithfully serves the domain.
- **Relational vs JSONB:** Adding it as a relational column (rather than burying it in the `supporting_evidence` JSONB) is the correct implementation choice because `action` is a core operational routing field (e.g., "Restart Service") that consumers will likely want to filter or group by in future dashboard queries, much like `category`.

### Consequences

**Pros**
- Fully preserves `Recommendation` aggregate integrity.
- Resolves a documentation omission without breaking any tests or frozen domain engines.
- Facilitates future dashboarding capabilities.

**Cons**
- None. This corrects an incomplete wording in the original specification.

---

## FE-001 — Action Center Retired; Recommendations Owns the Decision & Action Lifecycle

**Status:** Accepted

**Date:** 2026-08-05

### Context

Phase 10 Step 1 froze a six-workspace frontend architecture: Dashboard, Action Center, Investigations, Recommendations, Analytics, Administration. Action Center was scoped as "an operational work queue" surfacing active incidents, complaint spikes, SLA risks, and active investigations — everything "currently requiring operational attention."

A Product Architecture Review conducted before Phase 10 Step 3 scoping began found that Action Center's responsibility did not hold up as an independent workspace once examined against what it actually contained. Every item on its queue was, in substance, either: (a) something Investigations already owns the narrative for (active incidents, complaint spikes — both are Operational Story material), or (b) something Recommendations already owns the lifecycle for once a response exists (SLA risk mitigation, active-investigation follow-through). Action Center was not adding a distinct responsibility; it was re-surfacing other workspaces' content under a different label, which is exactly the "unrelated widgets on one page" pattern both the Dashboard architecture and the Product Experience Guide's workspace philosophy explicitly warn against (Section 2.2 — a workspace should be "a complete operational context," not a duplicate view).

The review also found that Action Center left a real gap unaddressed: nothing in the frozen six-workspace architecture explicitly owned what happens *after* a recommendation exists — approval, rejection, implementation tracking, and completed-action history. That gap was implicitly assumed to belong somewhere, but no workspace claimed it.

### Decision

Retire Action Center as a standalone workspace. Its route, navigation entry, workspace component, and dedicated icon are removed. Its "requires operational attention" framing is replaced by giving Recommendations explicit, complete ownership of the operational decision-and-action lifecycle: recommendation review, approval, rejection, implementation status, monitoring, and completed actions — the gap Action Center never actually closed.

Refined workspace architecture: **Dashboard → Investigations → Recommendations → Analytics → Administration.**

This is a navigation and ownership refinement, not a redesign. Dashboard, Investigations, Analytics, and Administration are unchanged. Recommendations' existing structure (queue, history, status) is extended, not rebuilt. No business functionality (real approval/rejection workflows, real monitoring data) was implemented as part of this refinement — only the architectural placeholder structure was updated to reflect the new ownership, per the same "structure only" discipline every prior Phase 10 step has followed.

### Rationale

- **Why Action Center was removed**: it duplicated content rather than owning a distinct responsibility — a direct violation of the frozen architecture's own rule that "responsibilities must never overlap" between workspaces (Phase 10 Dashboard architecture) and the Product Experience Guide's insistence that a workspace represent "a complete operational context rather than an isolated software module" (Section 2.2).
- **Why Recommendations became the Decision & Action workspace**: it already owned "lifecycle management, history, and status" for recommendations — the natural, and only unclaimed, owner of what happens after a recommendation is made. Extending an existing owner's responsibility is lower-risk and more coherent than inventing a new home for orphaned functionality.
- **Why this better aligns with the product mission**: the Product Experience Guide's Principle 1 is that the platform exists to help users make and act on operational decisions, and "reduce cognitive effort" (Principle 4) by avoiding duplicate information across screens. A single workspace that carries a recommendation from discovery through to a completed action is a shorter, more coherent path than routing a user through a separate Action Center queue that re-lists the same items.
- **Why the refinement occurred before additional workspace implementation**: Phase 10 Step 3 is about to implement real, business-facing dashboard functionality. Correcting a structural overlap now costs one workspace removal and a handful of reference updates; correcting it after Step 3 builds real data-fetching, filtering, and interaction logic against Action Center would multiply the cost and risk regressions in shipped functionality. This is the same "smallest-impact solution preserving architectural correctness" principle every prior phase in this project has applied to genuine architecture conflicts.

### Migration Impact

- **Low risk.** Action Center held no real business logic or data-fetching (Phase 10 Step 1/Step 2 explicitly forbade implementing it) — every reference removed was structural (a route, a nav entry, a lazy import, an icon, a handful of doc-comment examples), not behavioral.
- Verified by direct repository search: every file referencing Action Center (13 files, all frontend) was located and either removed (the workspace itself) or updated (route table, navigation config, workspace type union, icon registry, and five doc-comment cross-references in shared components).
- Full verification suite (typecheck, lint, build, complete automated test suite) passes with no regressions. No test hardcoded a reference to Action Center or a fixed workspace count, so no test required updating for the removal itself.
- No backend service, API contract, or persisted data was affected — this is a frontend-only, presentation-layer refinement.

### Consequences

**Pros**
- Removes a workspace that duplicated content instead of owning a distinct responsibility, restoring "responsibilities must never overlap" as an actually-true property of the architecture, not just a stated intent.
- Closes the previously-unclaimed decision-and-action ownership gap explicitly, before Step 3 has to work around its absence.
- Fewer workspaces to keep in sync as Phase 10 Step 3 and beyond add real functionality — one fewer navigation entry, route, and workspace shell to maintain.
- Sets a precedent: workspace responsibilities are revisited and corrected when a genuine overlap is found, rather than carried forward indefinitely once frozen.

**Cons**
- None identified. Action Center had zero implemented business functionality to migrate, and no other phase or document depended on its existence (verified: it was never named in PRD.md, ARCHITECTURE.md, ROADMAP.md, or PRODUCT_EXPERIENCE_GUIDE.md).

---

## REC-003 — Minimal Recommendation Decision Persistence Without Attribution

**Status:** Accepted

**Date:** 2026-08-12

### Context

Step 7.X's capability audit found that Recommendation Decision/Lifecycle (Phase 10 Step 4/A-07) rendered an honest placeholder rather than fabricated data, but no domain concept of a "decision" existed anywhere in `recommendation_service` — not a wiring gap, but a missing domain concept requiring an explicit decision before any implementation could begin (see `docs/architecture/phase-10/STEP_7X_SCOPE_FREEZE.md`, G-01).

The natural, complete version of "record a decision" would include who made it and what authority they had to make it. Neither exists in this platform: there is no authentication, no user model, and no RBAC (Phase 13, per `ROADMAP.md`). Building attribution now would mean inventing a throwaway identity concept purely to satisfy this one feature, one that would almost certainly conflict with or be discarded by the real Phase 13 authentication design.

### Decision

`RecommendationEntity` gains three new, nullable, additive columns: `decision` (enum: `pending`/`approved`/`rejected`/`deferred`), `decision_note` (free text), and `decided_at` (server-set timestamp). A single `PATCH /recommendations/{recommendation_id}/decision` endpoint records or overwrites these three fields. No decision-owner, actor, approval-authority, or audit-trail field is introduced anywhere in this design. Repeated PATCH calls unconditionally overwrite the prior decision — there is no conflict detection, since conflict detection would itself require knowing who is in conflict with whom.

### Rationale

- **Minimal-viable over speculative-complete:** a decision record answering only "what is the current state and optional note" is a real, usable capability today. A decision record answering "who decided, and were they allowed to" is not achievable honestly without authentication, so attempting it now would mean either fabricating an identity or blocking the whole feature on Phase 13.
- **No throwaway modeling:** inventing a placeholder "decision owner" field now (e.g., a free-text name) would create a fake-looking real field — exactly the kind of "looks real but isn't" presentation Step 7.X exists to eliminate elsewhere (see A-07's own motivation). Omitting the field entirely is the honest choice, not a shortcut.
- **Forward-compatible:** adding an actor/owner column later, once Phase 13 authentication exists, is a pure additive migration — nothing about this design needs to be reworked or reversed to support it.
- **Consistent with existing persistence conventions:** the nullable-column, additive-migration approach mirrors REC-002's own precedent (adding `action` to `RecommendationEntity` without disturbing the frozen aggregate), and the overwrite-on-repeated-PATCH semantics are the simplest behavior consistent with having no attribution to arbitrate a conflict.

### Consequences

**Pros**
- Recommendation Decision becomes a real, persisted capability instead of an honest placeholder, closing the last major Recommendation Workspace gap from Phase 10 Step 4.
- `recommendation_id` and `incident_id` remain untouched and undisturbed — no new identifier concept was introduced.
- The design imposes no migration cost or rework risk on the eventual Phase 13 authentication work.

**Cons**
- A decision cannot currently answer "who approved this" or "was this an authorized approval" — genuinely absent until Phase 13. Any consumer of this data must not assume attribution exists.
- Because there is no conflict detection, two people editing the same recommendation's decision in quick succession will silently overwrite one another. This is an accepted, documented limitation of the prototype stage, not an oversight.

---

## COPILOT-001 — Copilot Tool Boundary, Read-Only Authority, and Investigation/Analytics Composition

**Status:** Accepted

**Date:** 2026-08-13

### Context

An external architecture review of the initial Phase 12 draft (`docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md`) found two P0 contradictions against the actual repository. First, the draft's topology diagram depicted "Analytics Service" and "Investigation Service" as real backend services peer to Root Cause/Business Impact Service; neither exists — `backend/services/` contains 9 services total, and "Investigation"/"Analytics" are Gateway-only aggregation code (`gateway_service/app/services/investigation_aggregator.py`, `analytics_aggregator.py`) composing calls to `anomaly_service`, `root_cause_service`, `business_impact_service`, `recommendation_service`, and `nlp_service`. Second, the draft's tool list named a "Recommendation Decision Tool" while the same document's own tool-security section forbade all decision mutations in Phase 12 — a direct self-contradiction, since the only decision-related endpoint that exists (`PATCH /recommendations/{id}/decision`) is a real mutation.

### Decision

1. **No `investigation_service` or `analytics_service` is introduced.** The Investigation Tool and Analytics/Trend Tool are Copilot-owned, read-only composition adapters that call the real downstream services directly (§8/§9 of the Phase 12 architecture), never the public Gateway. Gateway's existing aggregators remain the sole implementation backing the public API and are unmodified.
2. **No extraction of Gateway's aggregation logic into `backend/shared/` is performed for Phase 12.** The resulting duplication between Gateway's aggregators and Copilot's tool adapters (both compose the same underlying service calls) is an accepted, conscious tradeoff, not an oversight — revisit only if the two implementations are found to drift in substance, not presentation.
3. **"Recommendation Decision Tool" is renamed to "Recommendation Decision Status Tool"** and is strictly read-only: it may read `decision`/`decision_note`/`decided_at` from the existing `GET /recommendations/{id}` response; it must never call `PATCH /recommendations/{id}/decision`.
4. **Every Phase 12 Copilot tool is read-only, as an absolute, cross-batch invariant.** No generic HTTP tool, no arbitrary-URL tool, no direct-database tool, no service-internal execution tool. Every known mutation endpoint on every domain service (`PATCH /recommendations/{id}/decision`, `PATCH /root-causes/{id}/confirm`, `PATCH /root-causes/{id}/reject`, `POST /root-causes/{id}/refresh`) is explicitly, individually excluded from the tool registry.

### Rationale

- **Honesty over convenience:** naming a nonexistent service in the architecture would have propagated a false assumption into every subsequent implementation batch's tool-adapter design.
- **Read-only is the single load-bearing security property of Phase 12** (no authentication exists yet — Phase 13). An ambiguously-named tool is the most likely way a read-only boundary silently becomes a write boundary during implementation; resolving the name now removes that risk before any code exists.
- **No premature refactoring:** extracting a shared composition primitive now, before a second real consumer's needs are known in detail, risks building the wrong abstraction — the existing precedent throughout this platform (DATA-002, RCA-001, BI-006) is to accept bounded, service-local duplication over premature cross-service coupling.

### Consequences

**Pros**
- Every Phase 12 batch can be implemented against a topology and tool registry that actually matches the repository.
- The read-only boundary is unambiguous and individually verifiable per tool, per endpoint.

**Cons**
- Gateway's investigation/analytics composition and Copilot's tool adapters are two independent implementations of similar logic; they are not guaranteed to stay in sync automatically and must be kept consistent by convention and test coverage, not shared code.

---

## COPILOT-002 — Copilot Conversation Ownership and Retention

**Status:** Accepted

**Date:** 2026-08-13

### Context

Phase 12's architecture requires short-term conversation persistence for follow-up-question continuity (e.g., a user asking "Why?" after a prior answer). The initial draft required this capability without stating which service owns the resulting data, where it is stored, or how long it is retained — a gap inconsistent with this project's established documentation discipline for every other persisted entity (ARCH-002, DATA-002, RCA-001, BI-006, REC-003 all state persistence ownership explicitly).

### Decision

`copilot_service` owns conversation persistence in the platform's existing shared PostgreSQL instance (ARCH-002), via two service-owned tables (conceptual, not yet implemented): `copilot_conversations` and `copilot_messages`. No other service ever reads or writes these tables. Retention for the prototype is **no automatic expiry** — the same posture every other entity in this platform already has (no service anywhere implements TTL/archival today). Production retention/privacy policy (encryption posture, user-initiated deletion, automatic expiry) is explicitly identified as future production hardening, not a Phase 12 deliverable. Conversation history is explicitly distinct from, and is not a step toward, the long-term "Organizational Knowledge" vision (ARB-002/ARB-005) — it is never aggregated across users or referenced by any domain service.

### Rationale

- **Consistency with ARCH-002:** every service already persists its own entities in the shared database; conversation data is not a special case requiring new infrastructure.
- **Avoiding speculative design:** inventing a retention/archival subsystem now, before any real usage pattern exists, would be exactly the kind of premature complexity this platform's engineering discipline (see BI-003, ARB-003) consistently avoids elsewhere.
- **Explicit is better than implicit:** stating "no automatic expiry, revisit under Phase 13" is a real, documented decision a future engineer can find and challenge — silence would have looked like an oversight instead.

### Consequences

**Pros**
- Conversation persistence has a clear, unambiguous owner and storage location before any table is created.
- The prototype-vs-production retention distinction is explicit, preventing a future audit from mistaking "no TTL" for a missed requirement.

**Cons**
- Conversation content persists indefinitely in the prototype with no built-in purge mechanism — acceptable for this stage, but a real gap a production deployment must close (tracked here as future hardening, not deferred silently).

---

## OBS-002 — Intelligence Pipeline Dashboard Deferred Pending Real Domain Metrics

**Status:** Accepted

**Date:** 2026-08-13

### Context

The frozen Phase 11 architecture (`docs/architecture/phase-11/PHASE_11_ARCHITECTURE.md` §3.9) specified a third Grafana dashboard, "Intelligence Pipeline," backed by "service-owned domain metrics... anomalies detected, incidents correlated, recommendations generated, business impact assessments by severity, etc." At Batch 4 closure, a repository-wide check confirmed zero `Counter`/`Histogram`/`Gauge` domain metrics exist anywhere in any service — only the shared HTTP metrics (Batch 1) exist. No Phase 11 batch's backend scope (Batch 1: logging/correlation/metrics-foundation/health; Batch 2: tracing; Batch 3: reliability/error-visibility; Batch 4: "Backend: None — consumes Batches 1–3's output only") ever committed to implementing these metrics. The top-level `ARCHITECTURE.md` §10 that originally named them uses only aspirational language ("may include," "should support") without specifying exact semantics, ownership, or instrumentation points.

### Decision

Dashboard 3 ("Intelligence Pipeline") is deferred out of Phase 11. Phase 11 closes with two Grafana dashboards — Platform Health and API & Service Performance — both backed entirely by real, already-implemented telemetry. Building Intelligence Pipeline is deferred to a future initiative that first adds real domain-metric instrumentation to the owning services (anomaly_service, root_cause_service/anomaly correlation, recommendation_service, business_impact_service), each service defining and incrementing its own metric via the existing shared `Counter`/`Histogram`/`Gauge` factory (`backend/shared/observability/metrics.py`), exactly as §3.5 already describes. The Phase 11 Definition of Done (§7, item 7 of the frozen architecture) is amended: "Grafana ships exactly three dashboards" becomes "Grafana ships the two dashboards backed by telemetry that exists as of Phase 11 (Platform Health, API & Service Performance); Intelligence Pipeline is explicitly deferred pending domain-metric instrumentation."

### Rationale

- **No-fabrication principle:** instrumenting these metrics now, without any batch ever having specified their exact semantics (what precisely counts as "an anomaly detected," at which pipeline stage), would mean inventing business semantics to satisfy a dashboard — exactly what Phase 11's own dashboard-honesty rules (§3.9, "no dashboard renders a static or seeded number as if it were live telemetry") exist to prevent, generalized to metric *definition*, not just display.
- **Scope discipline:** Batch 4 was explicitly scoped as "Backend: None (consumes Batches 1–3's output only)" — a Grafana/visualization-only batch. Adding new domain instrumentation to four business services is backend/business-service work that was never part of any Phase 11 batch's committed scope.
- **This is the frozen architecture's own unsupported assumption**, not a missing implementation task: §3.9 assumed these metrics would exist by Batch 4 close, but no batch's plan ever built them.

### Consequences

**Pros**
- Phase 11 closes honestly, with every shipped dashboard panel backed by real, verified telemetry — no panel that can only ever show empty data.
- The eventual Intelligence Pipeline work is cleanly scoped: add real domain metrics to the owning services first, then build the dashboard against them — the same two-step pattern every other Phase 11 dashboard already followed (Batch 1–3 built the telemetry; Batch 4 visualized it).

**Cons**
- Phase 11 ships without a business-facing intelligence dashboard. Operators wanting anomaly/recommendation/business-impact volume visibility must wait for the future domain-metrics initiative.
- The frozen architecture's Definition of Done item 7 required a documented amendment rather than being met as originally written.
