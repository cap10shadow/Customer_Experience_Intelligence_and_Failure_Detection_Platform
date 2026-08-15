## Batch 2: Workspace → API → Backend Integration Architecture

The governing rule:

> **Every frozen frontend section gets a defined data path, even when that path intentionally terminates at a future capability.**

We do **not** fabricate backend capabilities just to make the matrix look complete.

The audit shows that no workspace is currently fully integrated, but substantial real backend capability already exists for Dashboard, Investigations, Recommendations, and Analytics. Administration is the largest backend gap. 

---

# 1. The overall model

Our integration architecture becomes:

```
```

```
┌────────────────────────────────────────────────────┐
│                    FRONTEND                        │
│                                                    │
│ Dashboard                                           │
│ Investigations                                      │
│ Recommendations                                    │
│ Analytics                                           │
│ Administration                                     │
└──────────────────────┬─────────────────────────────┘
                       │
                Workspace API
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│                    GATEWAY                         │
│                                                    │
│ /api/v1/dashboard                                  │
│ /api/v1/investigations                             │
│ /api/v1/recommendations                            │
│ /api/v1/analytics                                  │
│ /api/v1/administration                             │
└───────┬──────────────┬──────────────┬──────────────┘
        │              │              │
        ▼              ▼              ▼
   Existing       Existing        Existing
   Services       Services        Services
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                 PostgreSQL
```

But the important part is that **each workspace gets a workspace-facing API**, rather than exposing individual microservices directly.

---

# 2. Dashboard integration

The frozen Dashboard has four sections:

1.  Operational Brief 
2.  Decision Summary 
3.  Investigation Entry Points 
4.  Supporting Evidence 

The audit gives us a very clear mapping. 

## Dashboard API

We create a Gateway-facing aggregation:

```
```

```
GET /api/v1/dashboard
```

Conceptually:

```
```

```
DashboardResponse
├── operationalBrief
├── decisionSummary
├── investigationEntryPoints
└── supportingEvidence
```

### Operational Brief

Existing sources:

```
```

```
anomaly_service
├── GET /incidents
└── GET /anomalies
```

The Gateway aggregates them into the Dashboard's "brief" shape.

The backend does **not** need a new "OperationalBrief" domain entity.

This is presentation aggregation.

### Decision Summary

Source:

```
```

```
recommendation_service
└── GET /recommendations
```

The Gateway filters/ranks recommendations into the Dashboard's decision-opportunity presentation.

Again:

> **Decision Opportunity is a Dashboard presentation concept, not a new backend entity.**

### Investigation Entry Points

Aggregate:

```
```

```
anomaly_service
       +
root_cause_service
       +
business_impact_service
```

The Gateway produces a concise incident story.

### Supporting Evidence

**Do not invent a backend implementation.**

The frozen Dashboard architecture intentionally treats this as supporting/placeholder analytics. 

Therefore:

```
```

```
Supporting Evidence
        ↓
existing placeholder architecture
        ↓
no new backend capability in Step 7
```

That is an intentional boundary, not a missing integration bug.

---

# 3. Investigations integration

Investigations is where the Gateway aggregation becomes most important.

The frozen sections are:

```
```

```
Observation
Evidence
Root Cause Analysis
Business Impact
Recommended Next Step
```

The audit confirms that the necessary backend pieces already exist. 

## Investigation API

We create:

```
```

```
GET /api/v1/investigations/{incidentId}
```

The frontend sees **one Investigation response**.

The Gateway internally gathers:

```
```

```
anomaly_service
        │
        ├── incident
        └── anomalies
        │
        ▼
nlp_service
        │
        └── enrichment evidence
        │
        ▼
root_cause_service
        │
        └── root cause
        │
        ▼
business_impact_service
        │
        └── impact
        │
        ▼
recommendation_service
        │
        └── latest recommendation
```

### Why one endpoint?

Because the user is investigating **one Incident**, not five backend services.

The frontend should not have to orchestrate:

```
```

```
GET incident
GET anomalies
GET enrichment
GET root cause
GET business impact
GET recommendation
```

That orchestration belongs behind the Gateway.

The audit explicitly identifies the Investigation view as a 4–5 service aggregation keyed by `incident_id`. 

---

# 4. Investigation data transformations

We already know the exact transformations required.

### Root Cause

Backend:

```
```

```
cause = SERVICE_OUTAGE
confidence_score = 82
confidence_level = HIGH
```

Frontend expects:

```
```

```
headline = "Service outage"
confidence = ...
```

The Gateway/DTO layer maps the backend representation to the UI contract.

The audit explicitly recommends this mapping rather than changing the frozen component. 

### Business Impact

Backend gives five top-level fields:

```
```

```
financial
customer
operational
sla
reputation
```

Frontend expects:

```
```

```
BusinessImpactDimensionSummary[]
```

The adapter reshapes the five fields into the existing presentation structure.

### Evidence

Evidence combines:

```
```

```
NLP explainability metadata
+
anomaly explanation
```

into:

```
```

```
EvidenceItem[]
```

This is exactly the kind of transformation our integration layer exists to perform.

---

# 5. Investigation → Recommendation handoff

The frozen Investigation architecture already has the handoff concept.

The real integration becomes:

```
```

```
Investigation
      │
      │ recommendationId
      ▼
Recommendation route
      │
      ▼
GET /api/v1/recommendations/{recommendationId}
```

The audit notes that the existing frontend has the structural idea but currently doesn't actually consume real IDs. 

So Step 7 connects the existing architectural seam.

---

# 6. Recommendations integration

This one needs careful separation.

The frozen Recommendation Workspace contains seven sections, but **not all seven are currently backed by real backend capability**.

The audit confirms:

### Real backend capability

```
```

```
Overview
Rationale
```

using:

```
```

```
GET /recommendations/{recommendationId}
```



### Future capability

```
```

```
Alternative Options
Expected Outcome
Risk Assessment
Decision
Recommendation Lifecycle
```

The backend does not currently contain those concepts. 

This is extremely important.

## We do NOT fabricate those fields.

Instead:

```
```

```
Recommendation API
        │
        ├── real recommendation data
        │
        └── explicitly deferred capabilities
```

The existing frozen UX already handles these honestly.

---

# 7. Recommendation API

We create:

```
```

```
GET /api/v1/recommendations/{recommendationId}
```

Gateway downstream:

```
```

```
recommendation_service
└── GET /recommendations/{recommendationId}
```

For traceability, the response retains:

```
```

```
recommendationId
incidentId
```

so the Recommendation Workspace can link back to the originating Investigation/Incident.

---

# 8. Recommendation Decision — important architectural boundary

The audit says there is **no backend decision endpoint** and no recommendation status field. 

And our frozen Recommendation architecture deliberately says:

> the platform recommends; humans decide.

But the actual decision-capture capability belongs to the long-term recommendation lifecycle vision.

Therefore **Step 7 does not invent:**

```
```

```
POST /recommendations/{id}/approve
POST /recommendations/{id}/reject
```

unless we explicitly decide to pull that capability forward.

For now:

```
```

```
Decision
   ↓
future capability / read-only representation
```

This preserves the architecture instead of pretending a workflow exists.

---

# 9. Analytics integration

Analytics is more complicated because it has a mixture of:

-  real backend data 
-  missing analytical capabilities 
-  intentionally deferred capabilities. 

The audit gives us the exact split. 

---

## Executive Overview

Backend:

```
```

```
anomaly_service
```

using:

```
```

```
GET /trends
GET /trends/daily
```

This can become:

```
```

```
GET /api/v1/analytics/overview
```

or be part of:

```
```

```
GET /api/v1/analytics
```

We'll decide the precise endpoint grouping when we design the API contract, but architecturally the data source is real.

---

# 10. Trend Analysis

Existing backend provides:

```
```

```
/trends/*
```

but returns numeric aggregates.

The frontend expects:

```
```

```
Trend
Narrative
Supporting Evidence
```

The audit explicitly identifies the missing narrative-generation layer. 

So we need a decision:

### Option A — Gateway generates narratives

Not ideal because it starts putting analytical business logic into the Gateway.

### Option B — Analytics backend capability

Create an analytics/narrative domain capability that takes the raw trend data and produces:

```
```

```
TrendNarrative
```

### I recommend Option B.

The Gateway should aggregate and transform, **not become the analytics engine**.

So:

```
```

```
anomaly_service
       ↓
raw trends
       ↓
Analytics intelligence layer
       ↓
TrendNarrative
       ↓
Gateway
       ↓
Frontend
```

That maintains our Batch 1 rule:

> Gateway = integration intelligence, not domain intelligence.

---

# 11. Pattern Discovery

Currently:

```
```

```
NO backend capability
```

The frozen Analytics architecture expects:

```
```

```
Pattern
→ Narrative
→ Supporting Evidence
```

Therefore Pattern Discovery requires a genuine analytical capability.

This is **not a Gateway problem**.

It is a backend/domain capability.

We should design the extension point now:

```
```

```
Pattern Analysis capability
        ↓
PatternResponse
        ↓
Gateway
        ↓
Pattern Discovery
```

But we should **not invent a sophisticated ML algorithm during architecture design**.

The architecture defines the contract and ownership.

Implementation can determine the first valid deterministic/analytical implementation from the existing data.

---

# 12. Recommendation Effectiveness

This stays exactly as frozen:

```
```

```
FutureCapabilityPlaceholder
```

because there is no Outcome/Human Action tracking anywhere in the system. 

No fake API.

No fake effectiveness metrics.

No fabricated success rate.

This is a **future extension point**, not a Step 7 implementation requirement.

---

# 13. Organizational Insights

Currently:

```
```

```
NO backend synthesis capability
```

So:

```
```

```
raw analytical evidence
        ↓
organizational insight synthesis
        ↓
OrganizationalInsightsResponse
        ↓
Gateway
        ↓
Analytics
```

This belongs to the Analytics domain, not Gateway.

---

# 14. Strategic Opportunities

Same principle:

```
```

```
Analytics intelligence
        ↓
StrategicOpportunity[]
        ↓
Gateway
        ↓
Strategic Opportunities
```

But it **must never become a second Decision Workspace**.

Recommendations remains the only place that owns decision/action lifecycle.

This boundary is already frozen in Analytics architecture. 

---

# 15. Administration — this is the major decision

Administration is fundamentally different.

The audit says:

> **5 of 6 sections have zero corresponding backend capability.**



That means we cannot solve Administration simply by writing Gateway routes.

We would need new backend capability for:

```
```

```
Platform Overview
User & Access Management
Data Sources & Integrations
Platform Governance
Audit & Change History
```

And Intelligence Configuration has only the underlying hardcoded rules, not persisted configuration. 

---

# 16. What I recommend for Administration

**Do not fake integration.**

Instead, Step 7 architecture should establish Administration's backend boundary:

```
```

```
/api/v1/administration/*
```

with domain ownership split according to the architecture we froze in Step 6.

### Platform Overview

New platform metadata/configuration capability.

### User & Access Management

New identity/access capability.

### Data Sources & Integrations

New integration registry/configuration capability.

### Intelligence Configuration

Configuration persistence and API around existing intelligence rules.

### Platform Governance

Governance policy storage/retrieval.

### Audit & Change History

Audit event persistence/query capability.

The exact schemas/tables will be designed as part of the Administration backend implementation scope rather than pretending these already exist.

---

# 17. Important: Administration does not become a giant service

We should **not** create:

```
```

```
administration_service
```

containing every unrelated concern simply because the UI calls itself Administration.

Instead, Administration is a **frontend workspace**.

Its backend capabilities can be owned by appropriate platform/domain services.

For example:

```
```

```
Administration Workspace
        │
        ├── identity/access capability
        ├── platform configuration capability
        ├── integration registry capability
        ├── intelligence configuration capability
        ├── governance capability
        └── audit capability
```

The Gateway presents them as one coherent administrative API.

This preserves the distinction between **workspace ownership** and **backend service ownership**.

---

# 18. Final workspace integration matrix

This is the important Batch 2 artifact:

| WorkspaceCurrent backend readinessStep 7 treatment |          |                                                                                                          |
| -------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------- |
| **Dashboard**                                      | High     | Fully integrate existing data through Gateway                                                            |
| **Investigations**                                 | High     | Build multi-service aggregated API                                                                       |
| **Recommendations**                                | Partial  | Integrate real Overview/Rationale; preserve future placeholders                                          |
| **Analytics**                                      | Partial  | Integrate real trends; build/define missing analytical capabilities required by non-placeholder sections |
| **Administration**                                 | Very low | Establish new backend platform capabilities required by frozen architecture                              |

The audit reaches essentially this same readiness conclusion. 

---

# 19. Backend capability classification

To prevent scope confusion, every requirement now falls into one of four categories.

### A — Existing capability, only integration missing

Examples:

```
```

```
Incidents
Anomalies
Root Causes
Business Impact
Recommendations
Evaluations
Trend aggregates
```

→ **Step 7 integrates them.**

### B — Existing capability, needs an API/presentation boundary

Examples:

```
```

```
Dashboard aggregation
Investigation aggregation
Trend narratives
Configuration representation
```

→ **Step 7 creates the necessary integration/domain boundary.**

### C — Frozen UI capability intentionally deferred

Examples:

```
```

```
Alternative Options
Recommendation Effectiveness
Outcome tracking
```

→ **Do not implement.**

### D — Backend capability genuinely absent but required by the frozen architecture

Examples:

```
```

```
Pattern Discovery
Organizational Insights
Strategic Opportunities
Administration platform capabilities
```

→ **Architecture must explicitly decide whether Step 7 builds the minimum capability or formally defers it.**

This is the most important decision we still need to make.

---

# 20. The key scope decision

We shouldn't say:

> "Step 7 integrates everything."

That would force us to suddenly build an enormous new backend.

Instead, I recommend:

### Step 7 target

**Integrate all currently available operational intelligence end-to-end and establish the backend/API contracts for capabilities that the frozen frontend requires but that do not yet exist.**

Then explicitly defer capabilities whose underlying domain model is itself a future-phase concept.

That means:

```
```

```
Dashboard             → REAL
Investigations        → REAL
Recommendations       → PARTIAL REAL + DEFERRED
Analytics             → REAL DATA + MINIMUM ANALYTICS CAPABILITY
Administration        → ARCHITECTURE/API FOUNDATION + scoped backend capabilities
Future outcomes       → DEFER
Copilot               → DEFER to Phase 12
Observability         → Phase 11
Production hardening  → Phase 13
```

This keeps Step 7 substantial but **doesn't turn it into Phases 11–13.**

---

# 21. One more issue we must resolve before freezing

The audit found that the backend's existing services currently communicate through **direct shared-database reads**, not service APIs:

```
```

```
Anomaly
  → reads ingestion/NLP tables

Root Cause
  → reads anomaly tables

Business Impact
  → reads anomaly + root cause tables
```



And the intended Business Impact → Recommendation/Evaluation event chain is currently unwired. 

**We should not casually rewrite all of that during Batch 2.**

The Step 7 architecture should therefore initially treat those existing backend internals as **existing implementation reality**, while our new frontend integration boundary remains clean:

```
```

```
Frontend
   ↓
Gateway
   ↓
Backend public APIs
   ↓
existing domain internals
```

Then Batch 3 will decide which cross-service transitions genuinely need to be repaired versus which existing prototype-stage coupling we leave untouched.

---

# Batch 2 — What I would freeze

### Workspace API ownership

```
```

```
/api/v1/dashboard
/api/v1/investigations
/api/v1/recommendations
/api/v1/analytics
/api/v1/administration
```

### Workspace rules

**Dashboard**

-  Gateway aggregates existing operational data. 
-  No new Dashboard domain entity. 
-  Supporting Evidence remains intentionally deferred. 

**Investigations**

-  One incident-centric aggregated response. 
-  Gateway orchestrates multiple backend sources. 
-  Frontend does not perform multi-service orchestration. 
-  Existing evidence/confidence/business-impact semantics remain unchanged. 

**Recommendations**

-  Real recommendation data integrated. 
-  Incident traceability preserved. 
-  No fabricated decision/lifecycle backend. 
-  Future sections remain honest placeholders until their domain capability exists. 

**Analytics**

-  Real trends integrated. 
-  Analytics domain owns analytical synthesis. 
-  Gateway does not become the analytics engine. 
-  Recommendation Effectiveness remains deferred. 
-  No second decision mechanism. 

**Administration**

-  Backend capabilities are recognized as net-new. 
-  Gateway exposes them only once corresponding backend ownership exists. 
-  No fake admin data presented as real. 
-  Policy ownership remains exactly as frozen in Step 6. 

---

## And this gives us a much cleaner next batch.

### **Batch 3 should now handle the cross-service mechanics**

That's where we'll settle:

1. **Incident ID as the central correlation key** 
2.  Complaint → NLP → Anomaly → Incident chain 
3.  Incident → Root Cause 
4.  Root Cause → Business Impact 
5.  Business Impact → Recommendation 
6.  Business Impact → Evaluation 
7.  Recommendation → Decision 
8.  Recommendation → Lifecycle 
9.  Analytics data aggregation 
10.  Event vs synchronous HTTP 
11.  The currently broken BusinessImpactCompleted path 
12.  Idempotency 
13.  retries 
14.  transaction boundaries 
15.  partial failures 
16.  traceability 
17.  service ownership 
18.  whether/where we address the current cross-service DB-read coupling 

That is the batch where we can make the **deep backend integration decisions** without contaminating the clean workspace/API mapping we just established.