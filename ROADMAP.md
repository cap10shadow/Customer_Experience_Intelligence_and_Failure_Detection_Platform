# Roadmap

# Customer Experience Intelligence & Failure Detection Platform

This document describes where the platform stands today and what genuinely remains — it is forward-looking, not a build history. For the detailed current implementation status, see [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md). For architecture and the reasoning behind major decisions, see [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md). For the platform overview, setup, and full capability list, see [`README.md`](README.md).

---

## Current State

The platform has reached its completed prototype implementation and closure stage. The full intelligence pipeline (ingestion → NLP enrichment → anomaly detection → incident correlation → root cause analysis → business impact scoring → recommendation generation), the Gateway/BFF frontend integration, authentication and RBAC, recommendation decision attribution, Copilot, observability, backup/restore, a production-like Docker configuration, and CI are all implemented and independently verified. It remains an engineering prototype, not a deployed production service — there is no live traffic, no cloud deployment, and no external customers. One closure activity remains open (see [Final Validation](#final-validation)).

---

## Completed Foundation

- **Modular service architecture** — nine independently owned backend services behind a single Gateway/BFF, one shared PostgreSQL instance, one linear Alembic migration chain.
- **The full intelligence pipeline** — complaint ingestion, NLP enrichment, statistical anomaly detection, incident correlation, deterministic root-cause analysis, weighted business-impact scoring, and recommendation generation.
- **Authentication & session handling** — Gateway-owned JWT session in an HttpOnly, same-origin cookie; bcrypt password hashing.
- **RBAC** — `viewer`/`operator`/`admin`, enforced on every Gateway route.
- **Internal service trust** — shared-secret-protected internal mutation routes; Gateway-attested principal propagation.
- **Recommendation decision attribution & history** — server-derived, spoof-proof attribution with an append-only decision history.
- **Controlled first-user bootstrap** — no public registration, no default credentials.
- **AI Copilot** — natural-language querying over real evidence through seven structurally read-only tools, bounded orchestration, conversation persistence and ownership.
- **Observability** — structured logging, correlation IDs, metrics, distributed tracing, and operational dashboards.
- **Backup & restore** — verified `pg_dump`/`pg_restore` tooling with isolated-container integrity checks.
- **Production-like Docker configuration** — a separate, hardened Compose configuration alongside the development one.
- **CI automation** — backend tests, frontend checks, and configuration validation running on every push.
- **A fresh-database migration correction** — the platform now initializes cleanly from an empty database.
- **Professionalized documentation** — a current README, status document, architecture record, and decision log, free of stale or misleading claims.

---

## Remaining Improvements

Genuinely unfinished work, verified against the current repository.

### Product Experience

- **Role-aware frontend UX** — the frontend does not yet hide controls a user's role can't use; the Gateway's RBAC enforcement is authoritative and correct regardless, but a `viewer`-role user currently discovers a restriction only after a request is rejected.
- **A complete Administration experience** — two of the workspace's six sections (Platform Overview, Intelligence Configuration) show real data; the remainder are illustrative placeholders, self-labeled as such in code.
- **Root-cause decision actions exposed to users** — confirm/reject/refresh exist and work at the service layer but are not yet reachable through the Gateway or Copilot.

### AI / Copilot

- **An external LLM provider** — Copilot's orchestration, tool-calling boundary, and conversation handling are real and tested, but no real language model is configured in this environment; every verification exercises the honest no-provider fallback.

### Data & Intelligence

- **Surfacing evaluation output** — `evaluation_service` computes and persists real quality/explainability scores that no Gateway route, dashboard, or Copilot tool currently displays.
- **Ingestion service test coverage** — `ingestion_service` has no dedicated automated test suite, unlike its sibling services.

### Engineering

- **Broader real-LLM verification** — once a provider is configured, Copilot's tool-grounded reasoning should be verified against live model output, not only the deterministic fallback and scripted evaluation harness.

---

## Final Validation

One closure activity remains before the platform can be considered fully closed: a saved, honest, twelve-stage synthetic-data validation report, tracing ingestion through NLP, anomaly detection, incident correlation, root cause, business impact, evaluation, recommendation, analytics, Copilot, observability, and authentication/authorization end to end, distinguishing tested-successfully / partially-tested / unavailable / known-limitation for every stage. This is a validation and closure activity, not a product capability or an implementation phase. It has not yet been started.

---

## Future Direction

Potential post-prototype evolution, not committed work:

- **Long-term decision lifecycle** — extending the pipeline past recommendation generation into human action capture, outcome tracking, and organizational-knowledge accumulation that informs future intelligence (per the platform's Architecture Review Board vision — see [`docs/ADR_ARCHITECTURE_REVIEW_BOARD.md`](docs/ADR_ARCHITECTURE_REVIEW_BOARD.md)).
- **Per-organization configurability** of the business-impact scoring model, while keeping the underlying engine deterministic and explainable.
- **Richer, role-specific experiences** once role-aware frontend UX exists as a foundation.
- **Expanded ingestion and validation datasets**, beyond the current sample/synthetic data.
- **Production-scale deployment considerations** — the current production-like Docker configuration is a hardened prototype topology, not a cloud deployment; real infrastructure, secret rotation, and scaling would be a distinct, later effort.

These are possibilities consistent with the platform's product requirements and architecture, not scheduled milestones.
