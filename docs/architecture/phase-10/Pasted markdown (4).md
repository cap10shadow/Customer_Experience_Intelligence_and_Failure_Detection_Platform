# Batch 4A — API & Data Contract Architecture

## 1. The governing principle

The contract boundary is:

```
```

```
Frontend
   ↓
Frontend API Client
   ↓
Gateway Public API
   ↓
Gateway DTO / Aggregation
   ↓
Backend Service API
   ↓
Domain / Persistence
```

The frontend **does not consume backend service contracts directly**.

The Gateway owns the public frontend-facing contract.

This is especially important because the current backend APIs are inconsistent in their version prefixes: anomaly/root-cause/business-impact already use `/api/v1`, while ingestion/NLP do not. The audit explicitly identified this as something requiring a convention decision. 

### Freeze

**All frontend-facing APIs use** **`/api/v1`****.**

Backend internal routes can retain their current implementation during migration.

---

# 2. Don't create one giant `/dashboard` API that returns the entire universe

We need to avoid the opposite extreme.

The Gateway should expose **workspace-oriented read APIs**, but the underlying response should still be composed from domain capabilities.

The public structure becomes:

```
```

```
/api/v1/dashboard/*
/api/v1/investigations/*
/api/v1/recommendations/*
/api/v1/analytics/*
/api/v1/administration/*
```

Not:

```
```

```
/api/v1/everything
```

And not:

```
```

```
/frontend → every microservice
```

---

# 3. Dashboard contract

The Dashboard has four frozen sections:

```
```

```
Operational Brief
Decision Summary
Investigation Entry Points
Supporting Evidence
```

The audit confirms Dashboard requires cross-cutting data rather than one existing backend endpoint. 

## Public endpoint

```
```

```
GET /api/v1/dashboard
```

### Response concept

```
```

```
DashboardResponse
├── operationalBrief
├── decisionSummary
├── investigationEntryPoints
└── supportingEvidence
```

### Why one endpoint?

Because the Dashboard is an executive workspace.

The frontend shouldn't make:

```
```

```
GET trends
GET incidents
GET recommendations
GET business-impact
```

independently just to assemble the page.

The Gateway aggregates that information.

---

## 4. Dashboard → source mapping

| SectionSourceStatus        |                                |                     |
| -------------------------- | ------------------------------ | ------------------- |
| Operational Brief          | anomaly/trend + incident data  | Existing capability |
| Decision Summary           | recommendation data            | Existing capability |
| Investigation Entry Points | incident + root cause + impact | Existing capability |
| Supporting Evidence        | supporting analytics/evidence  | Partial / deferred  |

The important part is that the first three can be assembled from real backend capabilities.

The audit confirms the backend already exposes real trend, root-cause, business-impact and recommendation endpoints that the frontend simply isn't consuming yet. 

---

# 5. Investigation contract

This is the most important read contract in the platform.

The user opens **one incident**.

Therefore:

```
```

```
GET /api/v1/investigations/{incidentId}
```

### Response

```
```

```
InvestigationResponse
├── incident
├── observation
├── evidence
├── rootCause
├── businessImpact
└── recommendedNextStep
```

The frontend gets **one coherent investigation model**.

It does not know or care that the information originated from several services.

The audit explicitly identifies Investigation as a 4–5-service aggregation keyed by `incident_id`. 

---

# 6. Investigation source mapping

```
```

```
incident
   ← anomaly_service

observation
   ← anomaly_service

evidence
   ← ingestion + NLP + anomaly

rootCause
   ← root_cause_service

businessImpact
   ← business_impact_service

recommendedNextStep
   ← recommendation_service
```

The Gateway performs the aggregation.

### Crucial rule

The Gateway **does not calculate** root cause or business impact.

It retrieves and assembles them.

That distinction prevents the Gateway becoming a second intelligence engine.

---

# 7. Investigation DTO transformation

This is where we solve the existing frontend/backend mismatch.

The audit found that real backend root-cause data exists, but Investigation currently hardcodes its own narrative; likewise Business Impact has real five-dimension backend data while the frontend hardcodes its own summary. 

So:

```
```

```
Backend domain response
        ↓
Gateway DTO mapper
        ↓
InvestigationResponse
        ↓
Frontend API adapter
        ↓
existing Investigation components
```

### We do NOT rewrite the frozen components just because the backend shape differs.

The adapter conforms real data to the already-frozen presentation contract.

---

# 8. Recommendation contract

The real current backend capability is:

```
```

```
GET /api/v1/recommendations/{recommendationId}
```

The public Gateway contract becomes:

```
```

```
GET /api/v1/recommendations/{recommendationId}
```

The Gateway can initially proxy/transform the existing recommendation response.

### Response

```
```

```
RecommendationResponse
├── recommendationId
├── incidentId
├── summary
├── rationale
├── category
├── priority
├── confidence
└── traceability
```

The exact field names will be aligned with the existing backend and frontend types during implementation rather than inventing parallel names.

---

# 9. Recommendation traceability

This is non-negotiable:

```
```

```
recommendationId
       │
       └── incidentId
                │
                └── Investigation
```

The Recommendation Workspace already deliberately uses `incidentId` rather than an invented `investigationId`. The audit confirms this context boundary is clean. 

So the public recommendation DTO retains:

```
```

```
recommendationId
incidentId
```

---

# 10. Recommendation future sections

We do **not** create fake API fields for:

```
```

```
Alternative Options
Expected Outcome
Risk Assessment
Decision
Recommendation Lifecycle
```

The audit confirms the backend does not currently provide those capabilities, including the lack of a decision-write endpoint. 

Therefore:

```
```

```
RecommendationResponse
├── real recommendation data
└── future sections remain frontend capability placeholders
```

If we decide during implementation that some of those capabilities are sufficiently important to build **inside Step 7**, we'll add them as explicit backend capabilities rather than pretending they already exist.

---

# 11. Analytics contract

This is where we need to be stricter.

The backend already provides:

```
```

```
/trends
/trends/daily
/trends/categories
/trends/regions
/trends/sentiment
/trends/urgency
```

but the Analytics workspace currently consumes none of them. 

So we create:

```
```

```
GET /api/v1/analytics
```

### Initial response

```
```

```
AnalyticsResponse
├── executiveOverview
├── trends
├── patterns
├── organizationalInsights
├── strategicOpportunities
└── recommendationEffectiveness
```

But this does **not** mean every field exists immediately.

---

# 12. Analytics capability classification

### Real now

```
```

```
trends
```

from anomaly\_service.

### Needs new backend capability

```
```

```
patterns
organizationalInsights
strategicOpportunities
```

The audit confirms these don't exist in the backend today. 

### Intentionally future

```
```

```
recommendationEffectiveness
```

because outcome tracking doesn't exist.

Therefore the contract must allow capability-level absence without pretending it is a valid zero-value metric.

---

# 13. Don't put LLM logic in the Gateway

This is one decision I want to make explicitly now.

The audit identified Analytics narrative generation as an unresolved architectural decision and noted that `copilot_service` is currently an empty stub. 

I recommend:

```
```

```
Gateway
   ❌ generate insight
   ❌ generate narrative
   ❌ call LLM directly

Analytics/domain capability
   ↓
generates analytical result
   ↓
Gateway
   ↓
Frontend
```

Whether that analytical capability eventually belongs in a dedicated analytics service or an appropriately expanded existing service can be decided when we implement the missing capability.

**The contract doesn't need to decide the implementation technology yet.**

---

# 14. Administration contract

This one is different.

We should define the public namespace now:

```
```

```
/api/v1/administration/*
```

But **we should not pretend the backend exists.**

The audit is unequivocal: user/role/permission/policy/audit data has no backend source whatsoever. 

So the contract is an **architectural target**, not an immediately implementable proxy.

Proposed endpoints:

```
```

```
GET /api/v1/administration/overview

GET /api/v1/administration/users
GET /api/v1/administration/roles
GET /api/v1/administration/permissions

GET /api/v1/administration/integrations
GET /api/v1/administration/configuration

GET /api/v1/administration/governance

GET /api/v1/administration/audit-history
```

But these are classified:

**NEW BACKEND CAPABILITY REQUIRED.**

We don't implement empty routes merely to make the frontend look connected.

---

# 15. Domain APIs remain underneath

The Gateway-facing APIs are not replacements for domain APIs.

Conceptually:

```
```

```
                     Gateway
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
 /dashboard      /investigations   /recommendations
        │               │                │
        ▼               ▼                ▼
    anomaly        anomaly/root      recommendation
    recommendation cause/impact
```

The Gateway decides which domain APIs it needs.

---

# 16. Existing backend APIs we should actually reuse

The audit identified real backend endpoints that are currently orphaned from the frontend. 

At minimum, Batch 4A recognizes these as integration sources:

```
```

```
Anomaly
├── trends
├── trends/daily
├── trends/categories
├── trends/regions
├── trends/sentiment
├── trends/urgency
└── incidents

Root Cause
└── root cause endpoints

Business Impact
└── business impact endpoints

Recommendation
├── recommendations
├── recommendation statistics
└── generation/detail endpoints

Evaluation
├── latest/{incident_id}
└── history/{incident_id}
```

The precise existing paths should be preserved internally where practical and normalized behind the Gateway.

---

# 17. Evaluation deserves a contract even though there is no workspace

This is an example of something we shouldn't forget just because there isn't an Evaluation Workspace.

The backend provides evaluation data, but no frontend consumes it today. 

So:

```
```

```
Evaluation
   ↓
Recommendation / Analytics / future surfaces
```

is a backend capability with **no current primary consumer**.

We should not force it into Dashboard or Analytics merely because it exists.

It remains available as an integration capability.

---

# 18. API response envelope

I recommend **not wrapping every successful response in unnecessary boilerplate** like:

```
```

```
{
  "data": {
    ...
  }
}
```

unless the existing API conventions require it.

For normal successful workspace responses:

```
```

```
{
  "recommendationId": "...",
  "incidentId": "...",
  "summary": "...",
  "rationale": "..."
}
```

For errors, use the standardized error envelope from Batch 1.

This keeps the contract simple.

---

# 19. Pagination

We should **not add pagination everywhere**.

Only collections that can genuinely grow unbounded need it.

### Pagination candidates

```
```

```
Administration users
Administration audit history
Investigations list
Recommendations list
```

### No unnecessary pagination

```
```

```
single Investigation
single Recommendation
Dashboard summary
Analytics summary
```

The audit flagged pagination as a performance concern to assess, not a requirement to add it indiscriminately. 

---

# 20. Filtering

Same rule.

Don't create a giant query language.

Use explicit filters where the existing UX actually needs them.

For example:

```
```

```
GET /api/v1/investigations?status=active
```

rather than:

```
```

```
?filter[anything]=...
```

Analytics already has a frozen `selectedAnalysisPeriod`, so its API should eventually accept a bounded period/filter representation.

But we don't need to design every possible analytics filter today.

---

# 21. IDs

We freeze the following distinction:

| IDPurpose            |                                 |
| -------------------- | ------------------------------- |
| `complaint_id`       | source complaint                |
| `enrichment_id`      | NLP enrichment                  |
| `anomaly_id`         | detected anomaly                |
| `incident_id`        | central operational correlation |
| `root_cause_id`      | root-cause analysis             |
| `business_impact_id` | impact assessment               |
| `recommendation_id`  | recommendation                  |
| `evaluation_id`      | evaluation                      |

And:

```
```

```
incident_id
```

must survive all downstream contracts.

The database already has these relationships represented through foreign-key columns. 

---

# 22. API contract matrix

This is the actual Batch 4A artifact.

| Public APIBackend sourceAggregationStatus        |                                                        |                                |                     |
| ------------------------------------------------ | ------------------------------------------------------ | ------------------------------ | ------------------- |
| `GET /api/v1/dashboard`                          | anomaly + recommendation + incident-related services   | Gateway                        | **NEW aggregation** |
| `GET /api/v1/investigations/{incidentId}`        | anomaly + root cause + business impact + NLP/ingestion | Gateway                        | **NEW aggregation** |
| `GET /api/v1/recommendations/{recommendationId}` | recommendation service                                 | Minimal                        | **READY TO WIRE**   |
| `GET /api/v1/analytics`                          | anomaly trends + future analytics capability           | Gateway + analytics capability | **PARTIAL**         |
| `GET /api/v1/administration/overview`            | none currently                                         | N/A                            | **NEW CAPABILITY**  |
| `GET /api/v1/administration/users`               | none currently                                         | N/A                            | **NEW CAPABILITY**  |
| `GET /api/v1/administration/roles`               | none currently                                         | N/A                            | **NEW CAPABILITY**  |
| `GET /api/v1/administration/integrations`        | none currently                                         | N/A                            | **NEW CAPABILITY**  |
| `GET /api/v1/administration/governance`          | none currently                                         | N/A                            | **NEW CAPABILITY**  |
| `GET /api/v1/administration/audit-history`       | none currently                                         | N/A                            | **NEW CAPABILITY**  |

---

# 23. Backend → Frontend matrix

We also need the reverse direction, because the audit specifically found backend capabilities that the frontend forgot to consume. 

| Backend capabilityCurrent consumerDecision |                         |                                               |
| ------------------------------------------ | ----------------------- | --------------------------------------------- |
| Trend APIs                                 | None                    | **Connect to Analytics**                      |
| Root Cause API                             | Hardcoded Investigation | **Connect to Investigation**                  |
| Business Impact API                        | Hardcoded Investigation | **Connect to Investigation**                  |
| Recommendation statistics                  | None                    | **Evaluate actual UI need before exposing**   |
| Recommendation generation/detail           | None                    | **Connect where appropriate**                 |
| Evaluation latest/history                  | None                    | **Do not invent UI; preserve API capability** |

This is important: **not every backend endpoint must have a frontend consumer.**

Some are legitimate internal/future capabilities.

---

# 24. The "no fake contract" rule

From this point forward:

If we encounter:

```
```

```
Frontend expects X
Backend does not provide X
```

we classify it:

### A. Build it in Step 7

if it is necessary for completing the integration step.

### B. Add an intermediate Step 7.x

if it is a substantial missing capability.

### C. Defer it

if it belongs logically to a later phase.

### D. Remove the frontend expectation

**only if the frozen architecture itself is revised and explicitly re-approved.**

We do **not** quietly fake the data.

---

# 25. Final Batch 4A freeze

I would freeze these decisions now:

### Public API

```
```

```
/api/v1/*
```

### Frontend access

```
```

```
Frontend → Gateway only
```

### Gateway

```
```

```
BFF-style aggregation boundary
```

### Dashboard

```
```

```
GET /api/v1/dashboard
```

### Investigation

```
```

```
GET /api/v1/investigations/{incidentId}
```

### Recommendation

```
```

```
GET /api/v1/recommendations/{recommendationId}
```

### Analytics

```
```

```
GET /api/v1/analytics
```

with real trend data first and explicit capability boundaries for missing analytics intelligence.

### Administration

```
```

```
/api/v1/administration/*
```

as the target contract namespace, with backend implementation explicitly classified as new capability.

### IDs

`incident_id` is the central operational correlation key.

### DTO ownership

Gateway-facing DTOs are separate from backend domain models and frontend presentation models.

### Aggregation

Gateway aggregates; it does not perform domain intelligence.

### Future capability

No fake APIs/data for capabilities that don't exist.