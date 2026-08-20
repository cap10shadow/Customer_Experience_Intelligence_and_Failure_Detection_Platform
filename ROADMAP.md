# Roadmap

# Customer Experience Intelligence & Failure Detection Platform

This document describes where the platform stands today and what genuinely remains — it is forward-looking, not a build history. For the detailed current implementation status, see [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md). For architecture and the reasoning behind major decisions, see [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md). For the platform overview, setup, and full capability list, see [`README.md`](README.md).

---

## Current State

The platform has reached its completed prototype implementation and closure stage. The full intelligence pipeline (ingestion → NLP enrichment → anomaly detection → incident correlation → root cause analysis → business impact scoring → recommendation generation), the Gateway/BFF frontend integration, authentication and RBAC, recommendation decision attribution, Copilot, observability, backup/restore, a production-like Docker configuration, and CI are all implemented and independently verified. It remains an engineering prototype, not a deployed production service — there is no live traffic, no cloud deployment, and no external customers. The final closure activity is now complete (see [Final Validation](#final-validation)).

---

## Completed Foundation

- **Modular service architecture** — nine independently owned backend services behind a single Gateway/BFF, one shared PostgreSQL instance, one linear Alembic migration chain.
- **Dataset identity & versioning** (AD-12) — every complaint belongs to a real, isolated Dataset; extending a dataset creates a new version and re-analyzes its full, cumulative record set without destroying prior versions. Dashboard, Analytics, and the full detection/investigation/recommendation pipeline are all dataset-scoped, with no global-query fallback.
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

- **Role-aware frontend UX beyond the operator-gated write actions** — the frontend states the role requirement up front for the platform's operator-gated actions (recording a recommendation decision, root-cause confirm/reject/refresh, ingesting data, asking Copilot), so a `viewer` no longer discovers those restrictions only after a request is rejected. No other action is role-gated today; a broader role-shaped experience (different default views or navigation per role) remains future work. The Gateway's RBAC enforcement is authoritative regardless.
- **A complete Administration experience** — two of the workspace's six sections (Platform Overview, Intelligence Configuration) show real data, now marked with a "Real data" badge (AD-11); the remaining four are presentation-only, marked "Not yet operational," and disclose that on the page (AD-10). Making them real requires backend capability that does not exist yet (user/role administration, external system integration, an administrative audit trail).
- **Design system primitives not yet adopted repository-wide** — `shared/components/primitives/{Button,Card,DataTable,Modal}` (AD-11) are used by new work and one flagship retrofit; roughly 14 other hand-rolled workspace card components predate them and remain unmigrated, a deliberate scope decision (repository-wide migration is cosmetic churn against a working product, not a functional gap).
- **A bulk/CSV ingestion backend endpoint** — the Data workspace (AD-11) submits one real request per row against `ingestion_service`'s existing single-record endpoint; a genuine server-side bulk-import capability does not exist.

### AI / Copilot

- **An external LLM provider** — Copilot's orchestration, tool-calling boundary, and conversation handling are real and tested, but no real language model is configured in this environment; every verification exercises the honest no-provider fallback.

### Data & Intelligence

- **Surfacing evaluation output** — `evaluation_service` computes and persists real quality/explainability scores that no Gateway route, dashboard, or Copilot tool currently displays.
- **Cold-start anomaly sensitivity** — against an empty database every dimension has a zero baseline, so the zero-baseline rule classifies even low-volume activity as CRITICAL. A minimum-volume floor would resolve this.
- **Entity-scoped incident correlation** — correlation currently groups anomalies by time window and severity alone, so unrelated concurrent anomalies merge into one multi-signal incident rather than separating by region/category.
- **Sentiment-aware business impact** — `nlp_service` produces real sentiment classifications that never reach `business_impact_service`, which scores from anomaly/trend metrics only; the reputation dimension can therefore score `none` against a highly negative complaint population.
- **Dataset version comparison and report generation/export** (AD-12) — both were explicitly requested in the Dataset/DatasetVersion brief and explicitly deferred. A dataset's version history is browsable today, but there is no diff between two versions and no exportable report artifact anywhere in the platform.
- **Asynchronous dataset analysis** — `POST /api/v1/datasets/{id}/versions/finalize` is synchronous end-to-end (AD-12); a large dataset means a long-held request with no progress streaming. No task queue exists anywhere in the platform yet.

### Engineering

- **Broader real-LLM verification** — once a provider is configured, Copilot's tool-grounded reasoning should be verified against live model output, not only the deterministic fallback and scripted evaluation harness.

---

## Final Validation

Complete. A saved, honest, end-to-end synthetic-data validation was performed on 2026-08-16 against real running services and a genuinely fresh database, tracing ingestion through NLP, anomaly detection, incident correlation, root cause, business impact, evaluation, recommendation, Gateway APIs, Copilot, observability, backup/restore, and authentication/authorization, with every claim labelled by evidence type. Outcome: **complete with documented limitations** — no undocumented gaps were found. Full record: [`docs/VALIDATION_REPORT.md`](docs/VALIDATION_REPORT.md).

That validation also surfaced three genuine intelligence-quality observations now tracked under [Remaining Improvements](#data--intelligence): cold-start anomaly sensitivity, time-window-only incident correlation, and business-impact scoring not consuming NLP sentiment.

---

## Future Direction

Potential post-prototype evolution, not committed work:

- **Long-term decision lifecycle** — extending the pipeline past recommendation generation into human action capture, outcome tracking, and organizational-knowledge accumulation that informs future intelligence (per the platform's Architecture Review Board vision — see [`docs/ADR_ARCHITECTURE_REVIEW_BOARD.md`](docs/ADR_ARCHITECTURE_REVIEW_BOARD.md)).
- **Per-organization configurability** of the business-impact scoring model, while keeping the underlying engine deterministic and explainable.
- **Richer, role-specific experiences** built on the role-awareness foundation now in place.
- **Expanded ingestion and validation datasets**, beyond the current sample/synthetic data.
- **Production-scale deployment considerations** — the current production-like Docker configuration is a hardened prototype topology, not a cloud deployment; real infrastructure, secret rotation, and scaling would be a distinct, later effort.

These are possibilities consistent with the platform's product requirements and architecture, not scheduled milestones.
