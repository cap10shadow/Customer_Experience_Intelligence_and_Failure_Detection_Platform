
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
