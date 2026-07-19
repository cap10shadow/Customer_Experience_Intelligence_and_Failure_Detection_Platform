
# ENGINEERING WORKFLOW

**Project:** Customer Experience Intelligence & Failure Detection Platform

---

# Purpose

This document defines the standard engineering workflow used throughout the project.

The objective is to ensure every feature is designed, implemented, reviewed, verified, and documented consistently while maintaining a clean, scalable, and production-oriented codebase.

This workflow applies to all contributors, regardless of the development tool or AI assistant used.

---

# Engineering Principles

Every implementation should prioritize:

- Correctness over speed
- Maintainability over cleverness
- Explainability over unnecessary complexity
- Incremental delivery
- Production-oriented engineering practices
- Clear separation of responsibilities

The goal is to build a believable operational intelligence platform rather than simply completing roadmap items.

---

# Development Lifecycle

Every feature follows the same lifecycle.

## Phase 1 — Design

Before implementation:

- Define the objective.
- Identify affected components.
- Review architecture and database impact.
- Define acceptance criteria.
- Limit implementation scope.

No implementation begins without a clear design.

---

## Phase 2 — Implementation

Implement only the approved feature scope.

Implementation should:

- Follow existing project structure.
- Reuse shared components where appropriate.
- Avoid unrelated refactoring.
- Keep commits focused on a single logical change.

---

## Phase 3 — Review

Every completed implementation is reviewed for:

- Architecture consistency
- Code quality
- Maintainability
- Service boundaries
- API consistency
- Database impact
- Error handling
- Performance considerations

The objective is architectural correctness rather than stylistic perfection.

---

## Phase 4 — Runtime Verification

After review:

- Build affected services.
- Verify Docker Compose startup.
- Verify health endpoints.
- Verify Swagger/OpenAPI.
- Test affected API endpoints.
- Confirm database migrations.
- Review runtime logs for errors.

Only modified functionality is verified.

Previously verified functionality is not retested unless impacted.

---

## Phase 5 — Documentation

After successful verification:

- Update PROJECT_STATUS.md
- Record architectural decisions (if applicable)
- Update CHANGELOG.md
- Commit changes

---

# Feature Contract

Before implementing any feature, define:

- Objective
- Scope
- Files allowed to change
- Files excluded from modification
- Database impact
- API impact
- Acceptance criteria
- Verification checklist

The Feature Contract prevents unnecessary scope expansion.

---

# AI Collaboration Workflow

The project uses multiple AI systems, each contributing according to its strengths.

## ChatGPT

Responsibilities:

- Architecture
- System design
- Engineering decisions
- Code review
- Maintainability review
- Performance review
- Workflow planning
- Final implementation approval

---

## Claude

Responsibilities:

- Feature implementation
- Runtime debugging
- Unit testing
- Refactoring within approved scope
- Verification support

---

## Antigravity

Responsibilities:

- Project scaffolding
- Repository generation
- Multi-file boilerplate
- Structural updates
- Development acceleration

---

## Gemini

Responsibilities:

- Independent validation
- Alternative implementation ideas
- Performance suggestions
- Research support
- Second-opinion architecture reviews

---

## Human Responsibilities

The developer remains responsible for:

- Final technical decisions
- Running the application
- Runtime verification
- Testing
- Git history
- Merge decisions

AI assists engineering—it does not replace engineering judgment.

---

# Code Review Guidelines

Reviews focus on:

- Correctness
- Readability
- Maintainability
- Service ownership
- API design
- Database integrity
- Security considerations
- Performance implications

Reviews should avoid unnecessary stylistic changes.

---

# Runtime Verification Checklist

For each completed feature:

□ Docker builds successfully

□ Containers start successfully

□ Health endpoints pass

□ OpenAPI documentation loads

□ API endpoints behave correctly

□ Database migrations succeed

□ Logs contain no unexpected errors

□ Acceptance criteria satisfied

---

# Git Strategy

One verified logical feature equals one commit.

Recommended commit format:

feat(service):

fix(service):

refactor(service):

docs:

test:

chore:

Example:

feat(nlp): implement complaint enrichment pipeline

fix(ingestion): prevent duplicate complaint insertion

docs: update project status after Phase 4 Step 3

---

# Definition of Done

A feature is considered complete only when:

- Design approved
- Implementation complete
- Code reviewed
- Runtime verified
- Documentation updated
- Acceptance criteria satisfied
- Commit created

---

# Project Documentation

The following documents are maintained throughout development:

| Document                        | Purpose                       |
| ------------------------------- | ----------------------------- |
| ROADMAP.md                      | Long-term project plan        |
| ARCHITECTURE.md                 | System architecture           |
| DATABASE_SCHEMA_ARCHITECTURE.md | Database design               |
| DECISIONS.md                    | Architecture Decision Records |
| PROJECT_STATUS.md               | Current implementation status |
| CHANGELOG.md                    | Engineering history           |
| ENGINEERING_WORKFLOW.md         | Development workflow          |

---

# Guiding Principle

Every completed phase should leave the project in a deployable, understandable, and maintainable state.

The objective is continuous engineering progress through small, verified, and well-documented increments.

---

# Non-Goals

During MVP development, avoid:

- Premature optimization
- Unnecessary microservices
- Over-engineering
- Unrelated refactoring
- Technology changes without justification
- Features outside the approved scope

Engineering discipline is achieved by completing one verified milestone at a time.
