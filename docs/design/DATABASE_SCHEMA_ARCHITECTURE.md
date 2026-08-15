# DATABASE SCHEMA ARCHITECTURE — Customer Experience Intelligence Platform

---

# 1. DATABASE ARCHITECTURE OBJECTIVE

The database layer is designed to support:

* operational intelligence
* analytics workflows
* anomaly detection
* NLP enrichment
* future AI reasoning
* business impact analysis

The schema should prioritize:

* explainability
* maintainability
* operational realism
* analytics-friendly querying
* future extensibility

The objective is NOT extreme enterprise-scale optimization.

The objective is a believable operational intelligence data foundation.

# SCHEMA DESIGN PHILOSOPHY

The schema is intentionally designed around operational relationships rather than isolated records.

Customer complaints are treated as observable indicators of backend operational behavior.

Operational events are treated as system-level disruptions that may propagate into measurable customer dissatisfaction and business impact.

The schema therefore prioritizes:

- operational traceability
- explainable relationships
- analytics visibility
- future intelligence reasoning

over excessive normalization or enterprise-scale abstraction.

---

# 2. PRIMARY DATABASE TECHNOLOGY

Primary database:

* PostgreSQL

Reasons:

* strong relational modeling
* analytics-friendly querying
* indexing support
* transactional consistency
* JSON support if needed later
* future scalability

The schema should remain relational-first during MVP implementation.

---

# 3. CORE TABLES

The MVP database should initially contain:

| Table                 | Purpose                         |
| --------------------- | ------------------------------- |
| complaints            | customer complaint records      |
| operational_events    | backend operational disruptions |
| business_impacts      | financial/operational effects   |
| complaint_categories  | normalized category mapping     |
| severity_levels       | operational severity mapping    |
| regions               | normalized regional references  |
| ingestion_jobs        | ingestion observability         |
| complaint_event_links | correlation relationships       |

These tables are sufficient for:

* ingestion
* analytics
* anomaly detection
* operational correlation
* future AI enrichment

---

# 4. COMPLAINTS TABLE

The complaints table is the primary operational intelligence entity.

Core fields:

| Field                 | Type      | Purpose                        |
| --------------------- | --------- | -------------------------------|
| id                    | UUID      | internal identifier            |
| external_complaint_id | TEXT      | source dataset ID              |
| created_at            | TIMESTAMP | complaint timestamp            |
| complaint_channel     | TEXT      | complaint source               |
| region_id             | FK        | normalized region              |
| category_id           | FK        | complaint category             |
| complaint_text        | TEXT      | raw complaint                  |
| normalized_text       | TEXT      | cleaned text                   |
| severity_id           | FK        | operational severity           |
| sentiment_score       | FLOAT     | NLP enrichment                 |
| urgency_score         | FLOAT     | operational urgency            |
| escalation_flag       | BOOLEAN   | escalation indicator           |
| resolution_hours      | INTEGER   | resolution timing              |
| complaint_status      | TEXT      | lifecycle status               |
| churn_risk_score      | FLOAT     | business risk estimate         |
| related_event_id      | FK        | linked operational event       |
| ingestion_job_id      | FK        | ingestion traceability         |
| inserted_at           | TIMESTAMP | persistence timestamp          |
| complaint_frequency_7d| INTEGER   | recent complaint behavior      |
| repeat_issue_flag     | BOOLEAN   | recurring issue indicator      |
| complaint_cluster_id  | TEXT      | operational grouping reference |
---

# 5. OPERATIONAL_EVENTS TABLE

Represents backend operational disruptions.

Core fields:

| Field                        | Type      | Purpose                        |
| ---------------------------- | --------- | -------------------------------|
| id                           | UUID      | event identifier               |
| event_type                   | TEXT      | operational failure type       |
| event_source                 | TEXT      | originating subsystem          |
| region_id                    | FK        | impacted region                |
| severity_id                  | FK        | operational severity           |
| affected_service             | TEXT      | impacted service               |
| event_status                 | TEXT      | active/resolved                |
| start_time                   | TIMESTAMP | event start                    |
| end_time                     | TIMESTAMP | event resolution               |
| estimated_customers_impacted | INTEGER   | impact estimate                |
| estimated_financial_impact   | FLOAT     | business loss estimate         |
| detection_source             | TEXT      | monitoring/manual              |
| root_cause_hint              | TEXT      | preliminary diagnosis          |
| inserted_at                  | TIMESTAMP | persistence timestamp          |
| complaint_frequency_7d       | INTEGER   | recent complaint behavior      |
| repeat_issue_flag            | BOOLEAN   | recurring issue indicator      |
| complaint_cluster_id         | TEXT      | operational grouping reference |
---

# 6. BUSINESS_IMPACTS TABLE

Represents measurable operational/business consequences.

Core fields:

| Field                  | Type      | Purpose                   |
| ---------------------- | --------- | ------------------------- |
| id                     | UUID      | impact identifier         |
| complaint_id           | FK        | linked complaint          |
| estimated_revenue_loss | FLOAT     | projected loss            |
| refund_amount          | FLOAT     | compensation cost         |
| sla_breach             | BOOLEAN   | SLA violation             |
| retention_risk_score   | FLOAT     | churn probability         |
| escalation_cost        | FLOAT     | operational handling cost |
| inserted_at            | TIMESTAMP | persistence timestamp     |

---

# 7. NORMALIZATION TABLES

## complaint_categories

Purpose:
standardized category mapping.

Fields:

* id
* category_name
* category_description

---

## severity_levels

Purpose:
normalized severity references.

Fields:

* id
* severity_name
* severity_rank

---

## regions

Purpose:
normalized geographic references.

Fields:

* id
* region_name
* region_code

---

# 8. INGESTION_OBSERVABILITY TABLE

## ingestion_jobs

Tracks ingestion execution metadata.

Fields:

| Field             | Purpose            |
| ----------------- | ------------------ |
| id                | ingestion job ID   |
| source_name       | dataset source     |
| ingestion_type    | batch/API          |
| records_processed | ingestion volume   |
| records_failed    | ingestion failures |
| ingestion_status  | success/failure    |
| started_at        | job start          |
| completed_at      | completion time    |

This supports:

* ingestion traceability
* debugging
* operational monitoring
* analytics reproducibility

---

# 9. CORRELATION TABLE

## complaint_event_links

Represents many-to-many operational relationships.

Purpose:

* operational correlation
* anomaly relationships
* root cause analysis
* future AI investigations

Fields:

| Field             | Purpose                  |
| ----------------- | ------------------------ |
| complaint_id      | linked complaint         |
| event_id          | linked operational event |
| correlation_score | relationship confidence  |
| linked_at         | correlation timestamp    |
| correlation_type  | TEXT | temporal/regional/category |
---

# 10. RELATIONSHIP DESIGN

The schema should support:

complaints
→ regions

complaints
→ categories

complaints
→ severity_levels

complaints
→ operational_events

complaints
→ business_impacts

operational_events
→ regions

operational_events
→ severity_levels

This relationship structure enables:

* explainable analytics
* operational investigations
* anomaly detection
* root cause analysis
* future AI reasoning

---

# 11. INDEXING STRATEGY

The MVP should index:

| Table                 | Indexed Fields                     |
| --------------------- | ---------------------------------- |
| complaints            | created_at, category_id, region_id |
| operational_events    | event_type, start_time, region_id  |
| business_impacts      | complaint_id                       |
| complaint_event_links | complaint_id, event_id             |

Purpose:

* analytics query performance
* anomaly detection queries
* dashboard responsiveness
* operational investigations

Avoid premature optimization beyond these indexes.

Typical analytics queries expected during MVP:

- complaint volume trends over time
- regional complaint spikes
- category escalation patterns
- operational event impact analysis
- severity distribution analysis
- complaint-to-event correlation analysis

---

# 12. NORMALIZATION STRATEGY

The MVP should remain:

* moderately normalized
* analytics-friendly
* explainable
* maintainable

Avoid:

* over-normalization
* premature denormalization
* warehouse-style complexity
* distributed database patterns

The objective is maintainable operational intelligence.

---

# 13. FUTURE EXTENSIBILITY

The schema should later support:

* NLP enrichment pipelines
* AI copilots
* recommendation systems
* semantic retrieval
* anomaly clustering
* operational forecasting
* root cause intelligence

without major relational redesign.

---

# 14. MVP IMPLEMENTATION PHILOSOPHY

The schema is intentionally designed to evolve incrementally.

Implementation order:

1. stable ingestion
2. persistence validation
3. analytics visibility
4. anomaly intelligence
5. NLP enrichment
6. operational reasoning
7. AI-assisted workflows

This phased strategy prioritizes:

* maintainability
* explainability
* engineering discipline
* operational realism

The system should remain understandable at every stage of evolution.


# OPERATIONAL SIMPLICITY CONSTRAINT

The schema intentionally avoids premature enterprise-scale complexity.

The MVP does NOT require:

- distributed database patterns
- event sourcing architectures
- CQRS separation
- warehouse-first modeling
- highly denormalized OLAP structures
- streaming-first persistence

The objective is a maintainable operational intelligence platform that remains:

- understandable
- explainable
- analytics-friendly
- incrementally extensible
