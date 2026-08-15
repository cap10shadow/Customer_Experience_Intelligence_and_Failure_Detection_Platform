## Batch 1: Integration Foundation Architecture

### 0. Purpose

The purpose of Batch 1 is to establish the **technical boundary between the existing frontend and existing backend**.

It must solve:

```
```

```
Frontend
   ↓
API contract
   ↓
Gateway
   ↓
Backend services
```

without changing the domain architecture already established.

The deep audit confirmed that this boundary currently doesn't exist in executable form: the frontend uses illustrative data, the gateway is effectively a health stub, and there is no frontend HTTP/API layer.  

---

# 1. The target integration architecture

This becomes our foundation:

```
```

```
                         ┌──────────────────────┐
                         │       React UI       │
                         │                      │
                         │ Dashboard            │
                         │ Investigations       │
                         │ Recommendations      │
                         │ Analytics             │
                         │ Administration       │
                         └──────────┬───────────┘
                                    │
                              API Client
                                    │
                              HTTPS / JSON
                                    │
                                    ▼
                    ┌─────────────────────────────┐
                    │        API Gateway          │
                    │          /api/v1            │
                    │                             │
                    │ Auth / Authorization       │
                    │ Routing                    │
                    │ Request validation         │
                    │ Aggregation                 │
                    │ DTO transformation         │
                    │ Error normalization         │
                    │ Correlation IDs             │
                    │ CORS                        │
                    └─────────────┬───────────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
       Ingestion              NLP/Analysis       Anomaly
       Service                Services            Service
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                         Root Cause / Impact
                                  │
                         Recommendation
                                  │
                           Evaluation
                                  │
                              Copilot
                                  │
                                  ▼
                            PostgreSQL
```

**Critical boundary:**

> The frontend never communicates directly with individual backend services.

Everything goes through the Gateway.

---

# 2. Gateway role — BFF/API Gateway

This is the first major decision.

### We use a **BFF-style API Gateway**.

It is more than a reverse proxy, but it is **not a business-domain service**.

### Gateway owns

-  API entry point 
-  authentication verification 
-  authorization enforcement at the API boundary 
-  routing 
-  request validation 
-  response aggregation 
-  DTO transformation 
-  error normalization 
-  timeout handling 
-  correlation/request IDs 
-  CORS 
-  API versioning 
-  downstream service configuration 

### Gateway does NOT own

-  complaint classification 
-  anomaly detection 
-  root-cause analysis 
-  business-impact calculation 
-  recommendation generation 
-  recommendation scoring 
-  evaluation logic 
-  persistence of domain entities 
-  domain business rules 

That distinction is essential.

```
```

```
Gateway
   = integration intelligence

Backend services
   = domain intelligence
```

The audit specifically identified aggregation as missing, so this BFF role is necessary for workspaces that require information from multiple services. 

---

# 3. API versioning

All frontend-facing APIs use:

```
```

```
/api/v1/...
```

Examples:

```
```

```
/api/v1/dashboard/...
/api/v1/incidents/...
/api/v1/recommendations/...
/api/v1/analytics/...
/api/v1/admin/...
```

### Rule

Backend internal service URLs are **not frontend contracts**.

For example, the frontend should never know:

```
```

```
http://anomaly-service:8003/...
```

That is an internal implementation detail.

---

# 4. API style

The integration API will use:

**REST + JSON over HTTP.**

We are not introducing GraphQL, gRPC, WebSockets, or another API paradigm merely because they are possible.

For the current platform:

```
```

```
GET       read
POST      create/action
PUT/PATCH  modify
DELETE    remove
```

The precise endpoint semantics will be designed in Batch 2/3 based on actual workspace requirements.

---

# 5. API contract strategy

This is one of the most important decisions.

We should **not** do this:

```
```

```
Backend Pydantic model
       ↓
directly exposed to React
```

Instead:

```
```

```
Backend Domain Model
        ↓
Gateway DTO
        ↓
OpenAPI Contract
        ↓
Generated/validated frontend API types
        ↓
Frontend View Model
```

FastAPI already provides OpenAPI schemas from its API definitions and Pydantic models, making OpenAPI a natural contract source for this stack. 

### Therefore:

**OpenAPI is the API contract authority.**

The gateway's public API should expose explicit response/request DTOs.

The frontend should consume the gateway contract rather than importing backend models.

This directly addresses the audit finding that frontend/backend types were independently authored and the shared contract locations are currently empty. 

---

# 6. Three model layers

We should explicitly preserve three different concepts.

### Domain model

Owned by backend service.

```
```

```
Complaint
Incident
Recommendation
Evaluation
...
```

### API DTO

Owned by Gateway API.

```
```

```
IncidentResponse
RecommendationResponse
DashboardSummaryResponse
...
```

### UI/View model

Owned by frontend.

```
```

```
IncidentViewModel
RecommendationViewModel
DashboardViewModel
...
```

This prevents backend schema changes from silently becoming frontend UI changes.

---

# 7. Frontend API architecture

The frontend changes from:

```
```

```
Component
   ↓
illustrative const
```

to:

```
```

```
Workspace
   ↓
Workspace data hook
   ↓
API module
   ↓
HTTP client
   ↓
Gateway
```

For example:

```
```

```
InvestigationsWorkspace
        ↓
useInvestigation()
        ↓
investigationApi.get()
        ↓
apiClient.get()
        ↓
/api/v1/investigations/{id}
```

### Central API client

There should be **one foundational HTTP client**, not every workspace creating its own `fetch()`/Axios configuration.

It owns:

-  base URL 
-  auth headers 
-  correlation ID 
-  JSON handling 
-  timeout 
-  common error parsing 
-  response handling 

Workspace-specific API modules own endpoint semantics.

---

# 8. Environment configuration

The existing `VITE_API_BASE_URL` should become an actual configuration input rather than dead configuration.

Conceptually:

```
```

```
Frontend
   VITE_API_BASE_URL
          ↓
      API Client
          ↓
       Gateway
```

No API URLs should be hardcoded into workspace components.

Similarly, backend service URLs should be configuration-driven.

---

# 9. Authentication boundary

The architecture should be:

```
```

```
User
 ↓
Frontend
 ↓
Gateway
 ↓
Authentication verification
 ↓
Authorization
 ↓
Backend
```

### Authentication mechanism

We will use an **OIDC/JWT-compatible authentication boundary**.

The architecture should not hard-code the platform to a specific commercial identity provider.

The Gateway validates:

-  token authenticity 
-  issuer 
-  audience 
-  expiry 
-  required claims 

The authenticated identity/claims are then propagated internally through a controlled mechanism.

### Important:

The frontend does **not** decide whether a user is authorized.

It can hide UI controls for usability, but the Gateway/backend remains authoritative.

---

# 10. Authorization

We need two levels.

### Gateway-level authorization

Examples:

```
```

```
Can view dashboard
Can view investigations
Can view recommendations
Can access administration
```

### Domain-level authorization

Examples:

```
```

```
Can approve recommendation
Can modify configuration
Can manage users
```

The second category remains owned by the appropriate domain/backend responsibility.

This aligns with the Administration architecture we already froze:

-  access policy → User & Access Management 
-  intelligence policy → Intelligence Configuration 
-  governance policy → Platform Governance 

We should not move those responsibilities into the frontend or generic Gateway logic.

---

# 11. Authentication propagation

We should not forward the user's raw external token indiscriminately to every service.

Instead:

```
```

```
External identity token
        ↓
Gateway validates
        ↓
Authenticated request context
        ↓
Controlled downstream identity/claims
```

The exact internal propagation mechanism will be finalized when we implement the gateway and backend security boundary.

The architectural rule is:

> Downstream services receive only the identity/authorization context they actually require.

---

# 12. Error architecture

This needs to be standardized now.

Every Gateway API should normalize failures into a consistent envelope.

Conceptually:

```
```

```
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Incident was not found.",
    "requestId": "..."
  }
}
```

We should distinguish at least:

```
```

```
400 → invalid request
401 → unauthenticated
403 → unauthorized
404 → resource not found
409 → state/conflict
422 → validation
429 → rate/usage limitation if introduced
502 → downstream service failure
503 → service unavailable
504 → downstream timeout
500 → unexpected server error
```

The frontend should not need to understand Python exceptions, database errors, or service-specific error structures.

---

# 13. Timeout and failure isolation

The Gateway must prevent one unhealthy backend service from hanging the entire frontend request indefinitely.

Therefore every downstream call gets:

-  explicit timeout 
-  bounded retry only where safe 
-  error classification 
-  correlation ID 
-  logging 

### Important:

We should **not automatically retry state-changing operations**.

For example:

```
```

```
GET → potentially retry
POST approve recommendation → do not blindly retry
```

---

# 14. Partial responses

This is especially important because we have aggregated workspace endpoints.

Suppose:

```
```

```
Investigation
 ├── anomaly ✓
 ├── root cause ✓
 └── business impact ✗
```

We should not automatically turn the entire response into a generic 500.

Instead, the architecture should distinguish:

### Required data unavailable

The workspace cannot meaningfully render.

→ request fails.

### Optional enrichment unavailable

The workspace can still render core information.

→ response contains explicit degraded state.

For example:

```
```

```
Investigation
 ├── core incident
 ├── findings
 ├── root cause
 └── business impact: unavailable
```

The frontend can then show its existing calm error/empty-state patterns.

---

# 15. Correlation IDs

Every external request gets a request/correlation ID.

```
```

```
Browser
   request-id
      ↓
Gateway
      ↓
Anomaly Service
      ↓
Root Cause Service
      ↓
Business Impact Service
```

The same correlation context should be available in logs.

This is essential once we have multiple services.

---

# 16. Observability boundary

Step 7 should establish **technical observability**, not build a new product monitoring dashboard.

We need:

-  request logs 
-  service logs 
-  correlation IDs 
-  latency 
-  HTTP status 
-  downstream failure visibility 

But we explicitly **do not turn Administration's Connection Health into DevOps monitoring**.

That boundary was frozen in Step 6.

So:

```
```

```
Technical observability
       ≠
Administration Workspace
```

---

# 17. CORS

CORS should be handled at the **Gateway**, not independently across every domain service.

Frontend:

```
```

```
Browser → Gateway
```

Gateway:

```
```

```
allowed frontend origin(s)
```

Backend services:

```
```

```
internal network
```

They should not be browser-facing APIs.

---

# 18. Internal network boundary

The intended topology is:

```
```

```
Internet / Browser
        ↓
     Frontend
        ↓
     Gateway
        ↓
  Internal services
        ↓
    PostgreSQL
```

The domain services and database should not be exposed directly to the browser.

This also simplifies:

-  security 
-  CORS 
-  authentication 
-  service discovery 
-  API versioning 

---

# 19. Service discovery/configuration

The Gateway should not hardcode service URLs throughout route handlers.

Instead:

```
```

```
Gateway configuration
 ├── INGESTION_SERVICE_URL
 ├── NLP_SERVICE_URL
 ├── ANOMALY_SERVICE_URL
 ├── ROOT_CAUSE_SERVICE_URL
 ├── BUSINESS_IMPACT_SERVICE_URL
 ├── RECOMMENDATION_SERVICE_URL
 ├── EVALUATION_SERVICE_URL
 └── COPILOT_SERVICE_URL
```

This allows Docker/local/dev/prod environments to provide different addresses.

---

# 20. Health endpoints

There should be two concepts.

### Gateway health

```
```

```
GET /health
```

Answers:

> Is the Gateway process alive?

### Gateway readiness

Potentially:

```
```

```
GET /ready
```

Answers:

> Is the Gateway ready to serve requests?

We should **not** make `/health` perform expensive downstream calls.

Downstream dependency readiness can be handled separately.

Again, this is technical infrastructure—not Administration's Connection Health UI.

---

# 21. Frontend state architecture

The existing workspace contexts remain responsible for **presentation state**.

They should NOT become data stores.

For example:

```
```

```
AnalyticsContext
   ├── activeSection
   ├── expandedSections
   └── selectedInsightId
```

It should **not** become:

```
```

```
AnalyticsContext
   ├── trends
   ├── recommendations
   ├── incidents
   └── metrics
```

Actual server data belongs in the API/data layer.

This preserves the architectural discipline we established across Steps 1–6.

---

# 22. Loading/error/empty states

Existing workspace UX already has these concepts.

Step 7 connects them to real data.

So:

```
```

```
API request
    │
    ├── loading → existing LoadingState
    │
    ├── success → real data
    │
    ├── empty → honest EmptyState
    │
    └── error → existing ErrorState/ErrorBoundary strategy
```

We do **not** redesign the five workspaces.

---

# 23. Future-phase extension boundary

This is the part you specifically asked about.

We explicitly design:

```
```

```
Gateway
   │
   ├── v1 Dashboard APIs
   ├── v1 Investigation APIs
   ├── v1 Recommendation APIs
   ├── v1 Analytics APIs
   ├── v1 Administration APIs
   │
   └── future API modules
```

And on the frontend:

```
```

```
API Client
   ├── dashboard/
   ├── investigations/
   ├── recommendations/
   ├── analytics/
   ├── administration/
   └── future modules
```

Future phases can add:

```
```

```
new endpoint
new DTO
new API module
new UI component
new backend capability
```

without restructuring the integration foundation.

### But:

**No speculative future components are implemented in Step 7.**

That is our explicit rule.

---

# 24. Testing foundation

Batch 1 also establishes the testing architecture.

We need four levels:

```
```

```
1. Unit
   ↓
2. API contract
   ↓
3. Gateway integration
   ↓
4. Full E2E
```

### Contract tests

Verify:

```
```

```
Gateway response
      ↕
OpenAPI contract
      ↕
Frontend expected type
```

### Gateway integration

Verify:

```
```

```
Gateway
   ↓
actual backend service
```

### E2E

Eventually:

```
```

```
Browser
 ↓
Frontend
 ↓
Gateway
 ↓
Backend
 ↓
Database
 ↓
response
 ↓
UI
```

The audit specifically identified the absence of true end-to-end integration testing as a major gap. 

---

# 25. What Batch 1 does NOT decide yet

To keep the batches efficient, we deliberately leave **domain-specific integration details** for later:

### Batch 2

Exactly which endpoints each workspace needs.

```
```

```
Dashboard → APIs
Investigations → APIs
Recommendations → APIs
Analytics → APIs
Administration → APIs
```

### Batch 3

Cross-service orchestration:

-  recommendation generation 
-  evaluation 
-  lifecycle 
-  event flow 
-  pipeline triggering 
-  cross-service IDs 

### Batch 4

Verification/hardening:

-  complete E2E matrix 
-  contract tests 
-  failure scenarios 
-  security tests 
-  performance considerations 
-  deployment integration 

So we aren't leaving anything out. We're putting each decision at the **correct architectural level**.

---

# Batch 1 — Proposed Freeze

I would now consider these **foundation decisions frozen**, unless the later audit-to-architecture mapping exposes a contradiction:

| AreaDecision                  |                                             |
| ----------------------------- | ------------------------------------------- |
| External API                  | REST/JSON                                   |
| API version                   | `/api/v1`                                   |
| Entry point                   | Gateway only                                |
| Gateway role                  | BFF-style API Gateway                       |
| Domain logic                  | Backend services                            |
| Frontend direct service calls | **Forbidden**                               |
| Public API contracts          | Gateway DTOs                                |
| Contract authority            | OpenAPI                                     |
| Frontend types                | Generated/contract-aligned + UI view models |
| HTTP client                   | Centralized frontend client                 |
| Auth boundary                 | Gateway                                     |
| Auth model                    | OIDC/JWT-compatible                         |
| Authorization                 | Gateway + domain enforcement                |
| CORS                          | Gateway                                     |
| Service URLs                  | Configuration-driven                        |
| Error format                  | Standard Gateway error envelope             |
| Request tracing               | Correlation/request ID                      |
| Downstream timeout            | Mandatory                                   |
| Partial failure               | Explicitly modeled                          |
| Frontend contexts             | Presentation state only                     |
| Technical observability       | Gateway/service layer                       |
| Browser → backend services    | **Forbidden**                               |
| Browser → database            | **Forbidden**                               |
| Future capabilities           | Extension points only                       |
| Speculative future features   | **Not implemented**                         |
| Integration testing           | Contract + integration + E2E                |
| Domain endpoint design        | Batch 2                                     |
| Cross-service orchestration   | Batch 3                                     |
| Final hardening               | Batch 4                                     |

This gives us a **proper foundation without spending another five conversations deciding individual infrastructure properties**.

And because FastAPI already produces OpenAPI/JSON Schema from its API definitions, this contract approach fits the existing backend technology rather than introducing another schema system. 