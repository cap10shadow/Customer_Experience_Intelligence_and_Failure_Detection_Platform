# DOMAIN ENUMS AND OPERATIONAL CONSTANTS

# 1. OBJECTIVE

This document defines the shared operational vocabulary of the platform.

The goal is to ensure:

- platform-wide consistency
- analytics stability
- dashboard consistency
- explainable intelligence
- maintainable enrichment workflows
- operational clarity

This document acts as the authoritative source for:

- enums
- status values
- operational categories
- severity levels
- lifecycle stages
- recommendation priorities

---

# 2. DOMAIN VOCABULARY PHILOSOPHY

Operational intelligence systems require stable domain language.

The platform intentionally standardizes operational terminology to prevent:

- analytics fragmentation
- inconsistent classification
- dashboard inconsistency
- enrichment drift
- ambiguous operational meaning

Vocabulary should remain:

- explainable
- operationally meaningful
- analytics-friendly
- evolution-aware
- maintainable

---

# 3. COMPLAINT STATUS ENUM

Represents the operational lifecycle state of complaints.

## Proposed Values

- pending
- ingested
- normalized
- enriched
- analyzed
- correlated
- escalated
- resolved
- archived

---

# 4. PROCESSING STAGE ENUM

Represents internal intelligence processing progression.

## Proposed Values

- raw_ingestion
- preprocessing
- enrichment
- anomaly_analysis
- business_evaluation
- recommendation_generation
- completed

---

# 5. SOURCE CHANNEL ENUM

Represents the operational source of customer complaints.

## Proposed Values

- email
- chat
- support_ticket
- social_media
- mobile_app
- website_form
- call_center
- marketplace
- internal_system

---

# 6. CUSTOMER SEGMENT ENUM

Represents operational customer categorization.

## Proposed Values

- individual
- premium
- enterprise
- partner
- reseller
- unknown

---

# 7. CUSTOMER TYPE ENUM

Represents relationship type between customer and organization.

## Proposed Values

- new_customer
- existing_customer
- high_value_customer
- at_risk_customer
- churned_customer
- unidentified

---

# 8. OPERATIONAL AREA ENUM

Represents the operational business domain affected by complaints.

## Proposed Values

- logistics
- payments
- customer_support
- delivery
- inventory
- product_quality
- returns
- account_management
- subscription_services
- technical_platform

---

# 9. SERVICE TYPE ENUM

Represents the affected operational service category.

## Proposed Values

- fulfillment
- payment_processing
- customer_service
- delivery_operations
- digital_services
- subscription_management
- platform_operations

---

# 10. ISSUE CATEGORY ENUM

Represents high-level complaint classification.

## Proposed Values

- delivery_issue
- payment_issue
- product_issue
- support_issue
- technical_issue
- account_issue
- refund_issue
- subscription_issue
- service_delay
- operational_failure

---

# 11. ISSUE SUBCATEGORY ENUM

Represents granular operational issue classifications.

These should remain:

- explainable
- operationally useful
- analytics-friendly

Subcategories should evolve incrementally based on:

- dataset behavior
- operational investigations
- analytics workloads
- anomaly patterns

---

# 12. SENTIMENT LABEL ENUM

Represents customer sentiment classification.

## Proposed Values

- positive
- neutral
- negative
- highly_negative

The platform intentionally avoids excessive sentiment granularity during MVP stages.

---

# 13. URGENCY LABEL ENUM

Represents operational urgency classification.

## Proposed Values

- low
- medium
- high
- critical

Urgency classification should prioritize operational usefulness over predictive complexity.

---

# 14. ANOMALY TYPE ENUM

Anomaly vocabulary should support temporal operational reasoning.

The platform should remain capable of distinguishing between:

- sudden spikes
- gradual degradation
- recurring operational failures
- seasonal anomalies
- emerging operational patterns

Represents operational anomaly classifications.

## Proposed Values

- complaint_spike
- regional_spike
- category_spike
- sentiment_shift
- escalation_surge
- operational_degradation
- churn_risk_surge
- abnormal_pattern

---

# 15. ANOMALY SEVERITY ENUM

Represents operational anomaly severity.

## Proposed Values

- informational
- warning
- severe
- critical

Severity should remain operationally explainable.

---

# 16. ESCALATION PRIORITY ENUM

Represents business escalation urgency.

## Proposed Values

- routine
- elevated
- urgent
- executive_attention

---

# 17. RECOMMENDATION TYPE ENUM

Represents recommendation categories.

Recommendation categories should remain operationally actionable rather than theoretically optimal.

The MVP prioritizes:

- operational usefulness
- explainability
- escalation clarity
- execution simplicity

## Proposed Values

- operational_fix
- escalation
- customer_intervention
- process_optimization
- staffing_adjustment
- inventory_adjustment
- workflow_review
- monitoring_increase

---

# 18. RECOMMENDATION STATUS ENUM

Represents operational execution state.

## Proposed Values

- generated
- reviewed
- approved
- in_progress
- completed
- rejected

---

# 19. RECOMMENDATION PRIORITY ENUM

Represents operational importance.

## Proposed Values

- low
- medium
- high
- critical

---

# 20. MODEL VERSIONING PHILOSOPHY

Intelligence workflows should maintain model traceability.

Version-aware intelligence supports:

- enrichment reproducibility
- confidence comparison
- auditability
- model evolution
- operational explainability

The platform should preserve:

- model_name
- model_version
- enrichment_version

for all intelligence-producing workflows.

---

# 21. ENUM EVOLUTION STRATEGY

Operational vocabulary changes should remain centrally governed.

Uncontrolled enum growth creates:

- analytics instability
- dashboard fragmentation
- inconsistent intelligence outputs
- operational ambiguity

Vocabulary evolution should remain deliberate and operationally justified.

Domain vocabulary should evolve incrementally and intentionally.

The platform intentionally avoids:

- uncontrolled label expansion
- inconsistent operational terminology
- excessive category fragmentation

Vocabulary changes should remain:
The platform should intentionally preserve controlled fallback values such as:

- unknown
- other
- unclassified

where operational ambiguity is expected.

This prevents unstable taxonomy expansion during early operational growth.
- operationally justified
- analytics-aware
- backward-compatible where possible

---

# 22. FUTURE DOMAIN EVOLUTION

Future platform evolution may introduce:

- multilingual classifications
- hierarchical issue taxonomies
- semantic operational labels
- adaptive recommendation taxonomies
- workflow orchestration states
- tenant-specific vocabularies

The MVP intentionally keeps vocabulary manageable and operationally explainable.