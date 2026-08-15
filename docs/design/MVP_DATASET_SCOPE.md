# MVP DATASET SCOPE — Customer Experience Intelligence Platform

---

# 1. MVP DATA STRATEGY

The MVP should prioritize:

* operational realism
* manageable complexity
* explainable intelligence
* analytics readiness
* maintainability

The objective is NOT building a massive enterprise-scale data platform.

The objective is building a believable operational intelligence system capable of demonstrating:

* complaint ingestion
* operational event correlation
* anomaly detection
* business intelligence workflows
* future AI integration readiness

---

# 2. PRIMARY MVP DATASET

## Selected Dataset

CFPB Consumer Complaint Database

Reason for Selection:

* high-quality real complaint narratives
* operational/business-oriented issues
* timestamps
* issue categorization
* regional information
* large enough for realistic analytics
* suitable for NLP and anomaly analysis

This dataset provides realistic customer frustration patterns and operational complaint behavior.

The CFPB dataset is particularly valuable because complaints are tied to operational and financial service failures rather than generic sentiment.

This creates stronger realism for:

- operational anomaly detection
- root cause correlation
- escalation modeling
- business impact analysis
- complaint lifecycle analytics

The dataset contains behavior closer to real enterprise operational support systems than generic review datasets.

---

# 3. MVP DATASET SIZE

The MVP should intentionally use a controlled subset rather than the full dataset.

Recommended Size:

* 25,000 to 75,000 complaint records

Reasons:

* faster local iteration
* manageable PostgreSQL performance
* easier debugging
* realistic analytics scale
* lower infrastructure overhead
* simpler NLP experimentation

The objective is operational realism, not artificial scale.

---

# 4. MVP REQUIRED COLUMNS

Only retain columns relevant to operational intelligence.

Required Columns:

| Dataset Column               | Purpose                  |
| ---------------------------- | ------------------------ |
| complaint_id                 | unique tracking          |
| date_received                | temporal analysis        |
| product                      | product/service mapping  |
| issue                        | complaint categorization |
| state                        | regional analysis        |
| consumer_complaint_narrative | NLP intelligence         |
| company_response             | resolution context       |
| timely_response              | SLA analysis             |
| submitted_via                | channel analytics        |

These fields are sufficient for:

* trend analysis
* anomaly detection
* NLP enrichment
* business intelligence
* operational correlations

---

# 5. EXCLUDED COLUMNS

The MVP should intentionally ignore fields that do not contribute to operational intelligence.

Examples:

* consumer personal information
* company identifiers
* tags not tied to analytics
* highly sparse metadata
* irrelevant financial/legal fields

Reasons for exclusion:

* reduced complexity
* cleaner schema design
* faster ingestion
* maintainability
* analytics focus

---

# 6. SYNTHETIC EVENT STRATEGY

The MVP will generate synthetic operational events separately from complaint ingestion.

This separation is intentional.

Complaint data represents:

* customer-observed failures

Operational events represent:

* backend business/system disruptions

The system should later correlate both layers.

---

# 7. MVP EVENT TYPES

Initial operational events:

| Event Type             | Operational Meaning      |
| ---------------------- | ------------------------ |
| logistics_delay        | delayed delivery systems |
| payment_failure        | transaction disruption   |
| service_outage         | platform downtime        |
| support_overload       | excessive support queues |
| pricing_error          | billing inconsistencies  |
| authentication_failure | login/auth issues        |

These event types are sufficient for realistic operational simulations.

---

# 8. CORRELATION MODELING STRATEGY

The platform should support realistic event-to-complaint propagation.

Example:

payment_failure
→ increased billing complaints

service_outage
→ increased technical complaints

support_overload
→ increased customer support complaints

This enables:

* anomaly detection
* root cause analysis
* operational investigations
* future recommendation systems

---

# 9. MVP INGESTION FLOW

Initial ingestion flow:

Dataset File
→ Validation
→ Cleaning
→ Schema Mapping
→ PostgreSQL Persistence
→ Analytics Consumption

The MVP should prioritize:

* deterministic ingestion
* explainability
* reproducibility
* maintainability

---

# 10. DATA NORMALIZATION RULES

The ingestion layer should normalize:

| Data Type      | Normalization Rule          |
| -------------- | --------------------------- |
| timestamps     | UTC conversion              |
| complaint text | whitespace cleanup          |
| regions        | state normalization         |
| categories     | standardized enum mapping   |
| channels       | normalized submission types |

This ensures analytics consistency.

---

# 11. MVP DATABASE STRATEGY

Initial database design should prioritize:

* normalized relational structure
* indexed timestamps
* indexed categories
* indexed regions
* explainable joins
* analytics-friendly querying
* aggregation-friendly schema design

Avoid:

* premature denormalization
* distributed storage complexity
* warehouse abstractions
* event streaming infrastructure

---

# 12. MVP IMPLEMENTATION BOUNDARIES

The MVP intentionally excludes:

* distributed streaming
* Kafka/event buses
* real-time pipelines
* advanced orchestration
* vector databases
* large-scale distributed processing

The MVP focuses on:

* operational realism
* maintainable engineering
* believable intelligence workflows
* explainable analytics
* future AI compatibility

---

# 13. FUTURE SCALABILITY PATH

Future platform evolution may later include:

* streaming ingestion
* real-time operational monitoring
* AI copilots
* semantic complaint retrieval
* recommendation engines
* operational forecasting
* distributed event pipelines

These are future evolution paths, not MVP requirements.

The current focus remains:

* stable ingestion
* realistic operational modeling
* analytics readiness
* maintainable architecture

# IMPLEMENTATION PHILOSOPHY

The MVP prioritizes operational credibility over artificial technical complexity.

The system should evolve incrementally:

1. stable ingestion
2. clean persistence
3. analytics visibility
4. anomaly intelligence
5. NLP enrichment
6. operational reasoning
7. AI-assisted workflows

This phased approach ensures:

- maintainability
- explainability
- implementation realism
- engineering discipline

The platform should always remain understandable and operationally grounded.
