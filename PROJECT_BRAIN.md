# Customer Experience Intelligence & Failure Detection Platform — Original Vision (Historical)

This document originally captured the platform's pre-implementation vision, problem statement, positioning, goals, business domain, core entities, data sources, intelligence pipeline, and system philosophy.

Nearly all of that content is now owned, more accurately and currently, by:

- Vision, problem statement, positioning, goals/non-goals — [PRD.md](PRD.md), [README.md](README.md)
- Architecture, intelligence pipeline, system philosophy — [ARCHITECTURE.md](ARCHITECTURE.md)
- Formal architecture decisions and rationale — [docs/DECISIONS.md](docs/DECISIONS.md), [docs/ADR_ARCHITECTURE_REVIEW_BOARD.md](docs/ADR_ARCHITECTURE_REVIEW_BOARD.md)
- Core entity design (as originally proposed; superseded by the actual implementation) — [docs/design/CORE_ENTITY_SPECIFICATIONS.md](docs/design/CORE_ENTITY_SPECIFICATIONS.md), with the real schema in `backend/services/*/app/models/` and `backend/migrations/versions/`
- Candidate/data-source strategy — [docs/design/DATASET_AND_INGESTION_STRATEGY.md](docs/design/DATASET_AND_INGESTION_STRATEGY.md)
- Current implementation status — [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)

That duplicated material has been removed from this file rather than kept as a second, drifting copy.

One section is retained below: `docs/ADR_ARCHITECTURE_REVIEW_BOARD.md` (ADR-003) cites this document's original "§6" Business Domain section by number as part of its rationale. That section is kept here, unrenumbered, so the citation continues to resolve to real content.

---

# 6. Business Domain

The platform is designed for customer-centric businesses that receive large volumes of operational complaints and customer support interactions.

Target industries include:

- e-commerce platforms
- logistics and delivery companies
- fintech/payment platforms
- SaaS products
- telecom providers
- online marketplaces
- subscription-based digital services

These organizations often struggle to connect customer complaints with the underlying operational systems causing failures.

The platform focuses on transforming customer experience signals into operational and business intelligence.

The initial implementation will primarily focus on e-commerce and logistics operations, where customer complaints can be directly correlated with operational failures such as delivery delays, inventory shortages, payment issues, and warehouse bottlenecks.

The architecture is intentionally designed to remain adaptable to other industries in future iterations.
