# CORE ENTITY SPECIFICATIONS

# 1. OBJECTIVE

This document defines the concrete operational entities of the platform.

The goal is to establish:

- stable operational schemas
- explainable ownership
- analytics-oriented persistence
- intelligence-ready entity design
- scalable schema evolution

This document acts as the implementation contract for:

- SQLAlchemy models
- Alembic migrations
- repositories
- ingestion APIs
- intelligence enrichment workflows

---

# 2. PRIMARY OPERATIONAL ENTITY — COMPLAINT

The complaint entity represents the foundational operational record of the platform.

All intelligence workflows originate from complaint records.

The complaint entity should prioritize:

- operational stability
- ingestion simplicity
- traceability
- analytics readiness
- future enrichment compatibility

The complaint entity intentionally avoids heavy intelligence coupling.

---

# 3. COMPLAINT ENTITY — CORE RESPONSIBILITIES

The complaint entity is responsible for storing:

- raw complaint content
- customer metadata
- operational metadata
- ingestion metadata
- source tracking
- lifecycle state
- temporal tracking

The complaint entity should NOT directly contain:

- embeddings
- anomaly logic
- recommendation logic
- heavy NLP outputs
- large intelligence artifacts

These belong in extension entities.

---

# 4. COMPLAINT ENTITY — PROPOSED CORE FIELDS

## Identity Fields

- complaint_id
- external_reference_id

---

## Raw Complaint Fields

- complaint_text
- complaint_title
- complaint_source
- source_channel

---

## Customer Context Fields

- customer_region
- customer_segment
- customer_type

---

## Operational Context Fields

- product_category
- operational_area
- service_type

---

## Temporal Fields

- event_occurred_at
- ingested_at
- updated_at

---

## Lifecycle Fields

- complaint_status
- processing_stage
- is_deleted

---

## Metadata Fields

The platform should preserve source-level traceability for operational investigations.

Operational records should remain attributable to:

- ingestion pipeline
- source platform
- dataset origin
- ingestion batch
- normalization workflow
- ingestion_source
- ingestion_batch_id
- source_record_hash

---

# 5. COMPLAINT ENTITY — OWNERSHIP

Primary owner:
- ingestion_service

Mutation responsibility:
- ingestion lifecycle
- normalization
- operational metadata correction

Other services should avoid mutating core complaint data directly.

Intelligence services should enrich through dedicated extension entities.

---

# 6. COMPLAINT ENRICHMENT ENTITY

The complaint enrichment entity stores intelligence outputs generated from complaint analysis workflows.

This entity exists separately to preserve:

- reprocessing capability
- model evolution
- explainability
- enrichment versioning
- operational auditability

Primary owner:
- nlp_service

The platform should support retaining historical enrichments rather than overwriting previous intelligence outputs.

This enables:

- enrichment comparison
- model evaluation
- confidence drift analysis
- intelligence auditing
- future ensemble intelligence workflows

---

# 7. COMPLAINT ENRICHMENT — PROPOSED FIELDS

## Relationship Fields

- enrichment_id
- complaint_id

---

## Classification Fields

- issue_category
- issue_subcategory
- sentiment_label
- urgency_label

---

## Intelligence Fields

- extracted_entities
- extracted_keywords
- summarized_issue

---

## Confidence Fields

- classification_confidence
- urgency_confidence
- sentiment_confidence

---

## Versioning Fields

- enrichment_version
- model_name
- model_version

---

## Temporal Fields

- enriched_at

---

# 8. ANOMALY EVENT ENTITY

The anomaly event entity stores operational anomalies identified through trend analysis and intelligence workflows.

Primary owner:
- anomaly_service

This entity should support:
Anomaly entities should prioritize explainability over opaque scoring.

Operational investigators should understand:

- why anomalies were triggered
- what signals contributed
- which operational dimensions were affected
- how severity was determined

- operational investigations
- trend analysis
- dashboard alerting
- anomaly explainability

---

# 9. ANOMALY EVENT — PROPOSED FIELDS

## Identity Fields

- anomaly_id

---

## Relationship Fields

- complaint_id
- related_region
- related_category

---

## Anomaly Fields

- anomaly_type
- anomaly_score
- anomaly_reason
- anomaly_severity

---

## Intelligence Fields

- triggering_pattern
- supporting_signals

---

## Temporal Fields

- detected_at

---

# 10. BUSINESS IMPACT ENTITY

The business impact entity stores operational and business-level risk estimations.

Primary owner:
- business_impact_service

This entity supports:
Business impact estimation should remain directional and operationally useful rather than financially absolute during MVP stages.

The goal is to support:

- prioritization
- escalation awareness
- operational focus
- business visibility

- operational prioritization
- business intelligence
- escalation workflows
- executive analytics

---

# 11. BUSINESS IMPACT — PROPOSED FIELDS

## Identity Fields

- impact_id

---

## Relationship Fields

- complaint_id
- anomaly_id

---

## Risk Fields

- churn_risk_score
- operational_risk_score
- revenue_risk_score
- escalation_priority

---

## Business Context Fields

- estimated_business_impact
- affected_operational_area
- impact_reasoning

---

## Temporal Fields

- evaluated_at

---

# 12. RECOMMENDATION ENTITY

The recommendation entity stores operational recommendations generated from intelligence workflows.

Primary owner:
- recommendation_service

The recommendation entity should remain:

Recommendations should remain operationally interpretable.

Users should understand:

- why actions were recommended
- what operational evidence supports them
- which anomalies or enrichments influenced them
- expected operational outcomes
- explainable
- traceable
- auditable
- operationally actionable

---

# 13. RECOMMENDATION — PROPOSED FIELDS

## Identity Fields

- recommendation_id

---

## Relationship Fields

- complaint_id
- anomaly_id
- impact_id

---

## Recommendation Fields

- recommendation_type
- recommended_action
- mitigation_strategy
- recommendation_priority

---

## Confidence Fields

- recommendation_confidence

---

## Execution Fields

- recommendation_status
- action_taken

---

## Temporal Fields

- generated_at
- resolved_at

---

# 14. RELATIONSHIP STRATEGY

Relationships should remain:

- operationally understandable
- analytics-friendly
- explainable
- maintainable

The platform intentionally prefers:

- explicit foreign keys
- moderate normalization
- clear ownership boundaries

The MVP intentionally avoids:

- deeply nested ORM graphs
- highly coupled bidirectional relationships
- premature relationship abstraction

---

# 15. INDEXING STRATEGY

Indexes should prioritize analytics and operational intelligence workloads.
The MVP intentionally avoids premature indexing complexity.

Indexes should evolve from:

- dashboard access patterns
- analytics bottlenecks
- anomaly query workloads
- operational filtering behavior
- temporal aggregation frequency

This preserves maintainability during early platform evolution.

Expected query patterns include:

- temporal complaint aggregation
- region-based filtering
- issue-category analysis
- urgency filtering
- anomaly investigation
- dashboard aggregation
- operational trend analysis

Indexes should evolve based on observed operational workloads.

---

# 16. ENTITY VERSIONING STRATEGY

Intelligence entities should support version-aware enrichment workflows.

This supports:

- model upgrades
- enrichment reproducibility
- confidence recalculation
- historical comparison
- intelligence auditability

The platform intentionally separates raw operational persistence from evolving intelligence layers.

---

# 17. FUTURE ENTITY EVOLUTION

The schema should support future additions including:

- vector embeddings
- semantic retrieval
- graph intelligence
- recommendation history
- feedback loops
- workflow orchestration
- multi-tenant support
- intelligence memory systems

These capabilities should evolve incrementally without major schema redesign.