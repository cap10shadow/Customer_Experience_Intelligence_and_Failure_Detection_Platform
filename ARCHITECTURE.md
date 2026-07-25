# System Architecture

# Customer Experience Intelligence & Failure Detection Platform

---

# 1. Architecture Philosophy

Per the Architecture Review Board (ADR-001; see `docs/ADR_ARCHITECTURE_REVIEW_BOARD.md`), the platform is formally named the **Customer Experience Intelligence & Operational Decision Support Platform**. Its purpose is to transform customer complaints into explainable operational intelligence and evidence-based business decisions. It is NOT merely a complaint analytics dashboard.

The system is designed as a modular operational intelligence platform that combines:
- backend services
- analytics pipelines
- AI/NLP intelligence
- business intelligence workflows
- recommendation systems
- executive-facing insights

The architecture prioritizes:
- modularity
- explainability
- scalability
- maintainability
- service separation
- operational observability

The system should resemble a modern AI-powered SaaS platform rather than a collection of disconnected ML models.

---

# 2. High-Level System Flow

## Current Flow (MVP and near-term roadmap)

Customer Signals
→ Data Ingestion
→ NLP Intelligence
→ Trend & Anomaly Detection
→ Incident Correlation
→ Root Cause Correlation
→ Business Impact Analysis
→ Recommendation Generation
→ Executive Dashboard & AI Copilot

## Long-Term Intelligence Lifecycle (Post-MVP Vision)

Per the Architecture Review Board (ADR-002), the platform's long-term architectural vision extends this flow from a one-way pipeline into a complete intelligence lifecycle:

Customer Signals
→ Data Ingestion
→ NLP Intelligence
→ Trend & Anomaly Detection
→ Incident Correlation
→ Root Cause Correlation
→ Business Impact Analysis
→ Recommendation Generation
→ Human Action
→ Outcome
→ Organizational Knowledge
→ Continuous Improvement
→ AI Copilot

This is a long-term vision only. It does not change the MVP scope, any current phase, or any completed engineering work. See §7 for how this maps onto the roadmap, and `docs/ADR_ARCHITECTURE_REVIEW_BOARD.md` for full rationale (ADR-002, ADR-005).

---

# 3. Architectural Style

The platform follows a modular service-based architecture organized within a shared monorepo structure.

Services are independently responsible for specific intelligence workflows while sharing common models, utilities, and infrastructure patterns.

The system is intentionally designed to:
- separate intelligence responsibilities
- isolate business logic layers
- support future scalability
- simplify independent development and testing

The architecture is NOT intended to simulate hyperscale distributed infrastructure.

The focus is:
- clean engineering design
- operational clarity
- intelligent workflows
- production-oriented structure

---

# 4. Core Architectural Layers

## A. Data Layer
Responsible for:
- complaint storage
- operational event storage
- analytics data
- historical trend tracking
- recommendation history

Primary technologies:
- PostgreSQL
- SQLAlchemy ORM

---

## B. Intelligence Layer
Responsible for:
- NLP understanding
- issue categorization
- anomaly detection
- incident correlation
- root-cause analysis
- business-risk estimation
- recommendation generation

Primary technologies:
- Python
- scikit-learn
- NLP models
- deterministic analytics pipelines
- rule-based operational intelligence
- statistical anomaly detection
- LLM-assisted summarization and reasoning

---

## C. AI Copilot Layer
Responsible for:
- natural-language querying
- operational summaries
- executive explanations
- AI-assisted investigation workflows

Primary technologies:
- LangGraph
- LLM APIs
- tool-calling workflows

---

## D. API Layer
Responsible for:
- frontend communication
- authentication
- request routing
- intelligence orchestration

Primary technologies:
- FastAPI
- JWT authentication

---

## E. Presentation Layer
Responsible for:
- dashboards
- operational visualizations
- risk heatmaps
- analytics views
- executive summaries

Per the Architecture Review Board (ADR-004), the Presentation Layer (Dashboard and AI Copilot) is responsible for letting users explore specific Business Impact dimensions, compare dimensions, and request business-specific explanations. The Presentation Layer adapts the **explanation**, never the **engine** — Business Impact calculations (§5, `business_impact_service`) remain identical for every user and every organization; only what is surfaced and how it is narrated differs.

Primary technologies:
- React
- TypeScript
- charting libraries

---

# 5. Core Services

The system is initially designed around modular backend services.

---

## ingestion_service

Responsibilities:
- ingest customer complaints
- ingest operational signals
- validate incoming data
- normalize records

Inputs:
- complaint datasets
- operational datasets
- API submissions

Outputs:
- structured complaint events

---

## nlp_service

Responsibilities:
- complaint classification
- urgency detection
- sentiment analysis
- issue extraction
- complaint enrichment

Outputs:
- enriched complaint intelligence

---

## anomaly_service

Responsibilities:
- complaint spike detection
- trend analysis
- anomaly monitoring
- regional issue tracking
- incident correlation

Outputs:
- anomaly alerts
- trend intelligence
- incident groups

Per the Architecture Review Board (ADR-007), the Incident this service produces is the platform's central lifecycle object. No separate "Case" entity exists or is planned — Root Cause, Business Impact, Recommendation, and (in the long-term vision) Human Action, Outcome, and Organizational Knowledge all attach to the Incident produced here.

---

## root_cause_service

Responsibilities:
- consume correlated Incidents from the Anomaly Service
- apply deterministic rule-based inference to identify probable root causes
- persist Root Cause records with structured evidence and confidence scoring
- manage Root Cause lifecycle (confirmation, rejection, recalculation)
- expose REST APIs for Root Cause retrieval and lifecycle management

Outputs:
- root-cause intelligence
- structured evidence records
- explainable confidence scores
- lifecycle-managed Root Cause resources

Confidence here (`confidence_score` / `confidence_level`) reflects this service's own definition — certainty that the correct deterministic rule fired. Per the Architecture Review Board (ADR-008), this is intentionally stage-specific and is not meant to be unified with confidence definitions used elsewhere in the platform (see §9).

---

## business_impact_service

Per the Architecture Review Board (ADR-003), the Business Impact Engine remains deterministic, explainable, rule-based, and generic. It always evaluates every dimension for every organization — no dimensions are disabled and no organization-specific scoring logic is introduced — and produces one authoritative Business Impact Assessment per Incident.

Responsibilities:
- evaluate Financial impact
- evaluate Customer impact
- evaluate Operational impact
- evaluate SLA impact
- evaluate Reputation impact
- combine all five dimensions into one authoritative, deterministically weighted assessment

Outputs:
- one Business Impact Assessment per Incident, carrying all five dimension evaluations, an overall severity, a business priority, and a deterministic explanation

Organization- or persona-specific emphasis on particular dimensions is a Presentation Layer concern (§4.E, ADR-004), never a `business_impact_service` concern — this service's output does not vary by organization or by viewer.

Confidence here reflects this service's own definition — the completeness of the available input data, not certainty of correctness. Per the Architecture Review Board (ADR-008), this is intentionally stage-specific (see §9).

---

## evaluation_service

The Evaluation Service acts as an independent Intelligence Assurance Service. It is NOT part of the operational intelligence pipeline and never modifies upstream services.

Responsibilities:
- observe completed intelligence via event-driven triggers (e.g., Business Impact completion event)
- execute a structured internal flow: Validation → Quality Engine || Explainability Engine (parallel) → Confidence Analyzer → Evaluation Builder → Persist Evaluation
- manage its own persistence for immutable Evaluation records
- track evaluation lineage via `evaluationVersion` and `previousEvaluationId`
- expose read-only external APIs for evaluation retrieval

Outputs:
- immutable Evaluation artifacts
- independent quality and explainability assessments

---

## recommendation_service

Responsibilities:
- generate operational recommendations
- prioritize mitigation actions
- suggest escalation paths

Outputs:
- recommended actions
- intervention priorities

---

## copilot_service

Responsibilities:
- AI-powered querying
- operational summaries
- executive explanations
- tool-calling orchestration

Outputs:
- explainable operational summaries
- intelligence-assisted investigation workflows
- business-facing operational insights

---

## gateway_service

Responsibilities:
- API routing
- authentication
- request orchestration
- frontend integration

Outputs:
- unified platform APIs

---

# 6. Database Design Philosophy

The database layer should:
- support analytical workloads
- preserve historical intelligence
- track issue evolution over time
- support explainability and traceability
- preserve historical intelligence evolution over time
- support longitudinal operational analysis

Core database categories:
- complaints
- operational events
- anomaly records
- root-cause mappings
- business-risk scores
- recommendations
- user queries
- AI-generated summaries

---

# 7. Intelligence Pipeline

## Current Pipeline (MVP and near-term roadmap)

Complaint/Event Ingestion
→ NLP Enrichment
→ Trend Detection
→ Anomaly Analysis
→ Incident Correlation
→ Root Cause Correlation
→ Business Impact Estimation
→ Recommendation Generation
→ Dashboard & Copilot Delivery

*(Note: The Evaluation Service operates out-of-band as an independent observer triggered by pipeline events. It is deliberately NOT a blocking step in this operational pipeline.)*

## Long-Term Lifecycle (Post-MVP Vision — ADR-002, ADR-005)

Complaint/Event Ingestion
→ NLP Enrichment
→ Trend Detection
→ Anomaly Analysis
→ Incident Correlation
→ Root Cause Correlation
→ Business Impact Estimation
→ Recommendation Generation
→ Human Action
→ Outcome
→ Organizational Knowledge
→ Continuous Improvement
→ Dashboard & Copilot Delivery

This lifecycle extension is a long-term architectural vision, not an MVP requirement. It does not change the current roadmap (see ROADMAP.md, "Long-Term Intelligence Lifecycle (Post-MVP Vision)").

---

# 8. Workflow Coordination Philosophy

The platform follows an orchestration-based intelligence workflow.

Each intelligence stage enriches platform data progressively:

raw complaints
→ enriched complaint intelligence
→ anomaly insights
→ incident groups
→ root-cause intelligence
→ business-risk scoring
→ operational recommendations

The system initially relies on synchronous service coordination through the gateway layer and shared persistence models.

As platform complexity evolves, selective asynchronous processing may be introduced for:
- long-running analytics
- AI summarization tasks
- batch intelligence generation
- large-scale anomaly processing

The architecture intentionally avoids premature distributed-event complexity during early development stages.

---

# 9. Explainability Requirements

All intelligence outputs must:
- reference supporting evidence
- expose contributing signals
- avoid hallucinated business claims
- remain operationally explainable

Examples:
- anomaly source references
- correlated operational events
- confidence scoring
- supporting complaint clusters

The system should prioritize trustworthy intelligence over flashy AI behavior.

## Evidence Chain (ADR-006)

Per the Architecture Review Board, every intelligence stage contributes evidence, and the platform conceptually maintains a connected evidence chain across Complaint → NLP → Anomaly → Incident → Root Cause → Business Impact → Recommendation. This is a conceptual principle, not an implementation requirement — each service continues to own its own explanation format (NLP enrichment fields, anomaly explanations, Root Cause `Evidence` objects, Business Impact `ImpactEvaluation` reasons); no shared schema or new service is introduced by this decision.

## Confidence (ADR-008)

Confidence is intentionally stage-specific. Each service owns and defines its own confidence concept — NLP classification confidence, anomaly severity (a magnitude-based proxy), Root Cause's `confidence_score`/`confidence_level` (certainty the correct rule fired), and Business Impact's `confidence` (completeness of available input data) are four distinct concepts that share a name but not a meaning. The architecture does not force these into one universal confidence score, and future work should not attempt to unify them.

---

# 10. Observability & Monitoring

Business-facing metrics may include:
- complaint spike frequency
- high-severity issue counts
- churn-risk trends
- operational-risk distribution
- recommendation generation frequency
- root-cause confidence distribution

The platform should support:
- service health monitoring
- intelligence pipeline metrics
- anomaly-processing metrics
- API latency tracking
- AI copilot request tracing

Future observability tools may include:
- Prometheus
- Grafana
- structured logging
- distributed tracing

---

# 11. Security Principles

The platform should:
- support JWT authentication
- isolate sensitive operational data
- validate all incoming requests
- avoid exposing internal intelligence pipelines publicly

Security is treated as a first-class engineering concern rather than an afterthought.

---

# 12. MVP Engineering Philosophy

The initial system implementation prioritizes:
- intelligence workflow correctness
- explainability
- modular engineering
- operational realism
- fast iteration

The MVP should favor:
- simple synchronous workflows
- clean modular services
- shared infrastructure patterns
- implementation clarity

The platform intentionally avoids:
- unnecessary distributed-system complexity
- premature scalability optimization
- infrastructure-heavy orchestration
- enterprise-scale deployment assumptions

Complexity should evolve only when justified by real platform behavior.