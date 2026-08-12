# Batch 3 — Cross-Service Pipeline & Communication Architecture

## 1. First: the target pipeline

We want the prototype to behave like this:

```
```

```
Complaint
   │
   ▼
NLP Enrichment
   │
   ▼
Anomaly Detection
   │
   ▼
Incident Correlation
   │
   ▼
Root Cause Analysis
   │
   ▼
Business Impact
   │
   ├──────────────► Recommendation
   │
   └──────────────► Evaluation
```

And the important distinction:

> **This is the target automated workflow. It is not what the repository currently does.**

Today, Complaint → NLP is manually triggered, NLP → Anomaly relies on direct DB reads, Anomaly → Incident is manually triggered, Incident → Root Cause is manually triggered, and Root Cause → Business Impact is manually triggered. 

---

# 2. Central correlation object: Incident

This is already strongly supported by the architecture.

`Incident` is the central lifecycle object, and downstream entities carry `incident_id`. 

So our primary lineage becomes:

```
```

```
complaint_id
     │
     ▼
enrichment
     │
     ▼
anomaly_id
     │
     ▼
incident_id  ← CENTRAL CORRELATION KEY
     │
     ├── root_cause
     │
     ├── business_impact
     │
     ├── recommendation
     │
     └── evaluation
```

### Architectural rule

**`incident_id`** **is the primary downstream business correlation key.**

We do **not** create an additional "investigation\_id".

That is consistent with the frozen Investigation architecture: Investigation is a presentation of one Incident, not a separate domain entity. 

---

# 3. But we also need event identity

`incident_id` tells us:

> **Which business incident does this belong to?**

`event_id` tells us:

> **Which processing event/transition is this?**

So they serve different purposes.

```
```

```
incident_id
→ business lineage

event_id
→ processing/idempotency
```

This is already reflected in the repository: `evaluation.event_id` and `recommendation_generation.event_id` have unique constraints, with application-level duplicate checks as well. 

We should preserve that design.

---

# 4. Target event envelope

We should standardize the conceptual event structure now.

Something like:

```
```

```
Event
├── event_id
├── event_type
├── occurred_at
├── incident_id
├── source_service
├── schema_version
└── payload
```

Example:

```
```

```
BusinessImpactCompleted
├── event_id
├── event_type
├── occurred_at
├── source_service
├── incident_id
└── payload
      └── business_impact_id
```

This gives us traceability without forcing every service to duplicate the entire upstream object.

**Important:** this is an architectural contract, not a requirement to introduce Kafka/RabbitMQ immediately.

---

# 5. Complaint → NLP

### Current

```
```

```
POST /complaints
       ↓
[stops]
       ↓
external caller
       ↓
POST /enrichments/process
```

The ingestion service has no publisher and NLP has no ingestion-event consumer. 

### Target

```
```

```
POST /complaints
       ↓
Complaint persisted
       ↓
ComplaintCreated event
       ↓
NLP consumer
       ↓
Enrichment persisted
```

### Decision

**Make this event-driven in the target architecture.**

But because there is currently **no broker**, the prototype can initially use the existing internal event mechanism / in-process abstraction.

We should build against an abstraction such as:

```
```

```
EventPublisher
EventConsumer
```

rather than hard-coding a broker.

That gives us:

```
```

```
Prototype:
In-process event implementation

Future:
Kafka/RabbitMQ/etc.
```

without rewriting domain logic.

---

# 6. NLP → Anomaly

This is where we need to be careful.

### Current architecture

Anomaly directly reads:

```
```

```
complaints
complaint_enrichments
```

through local SQLAlchemy table shims. 

This is documented as the `DATA-002` convention.

### Is that good architecture?

No, not as a long-term microservice boundary.

The audit explicitly identifies this as a genuine ownership-boundary violation: schema changes can silently break downstream services. 

### But should we rewrite it immediately?

**No.**

That would turn Step 7 into a database-boundary migration project.

So:

### Step 7 decision

Keep the existing read-model implementation temporarily.

But establish:

```
```

```
NLP
  owns enrichment

Anomaly
  consumes enrichment data
```

as the **logical ownership contract**.

Later, we can replace the DB read with:

```
```

```
EnrichmentCompleted
       ↓
Anomaly
```

without changing the anomaly domain logic.

---

# 7. Anomaly → Incident

Current:

```
```

```
POST /anomalies/run
       ↓
POST /incidents/run
```

The correlation engine exists, but the transition is not automatically triggered. 

Target:

```
```

```
AnomalyDetected
       ↓
Incident Correlation
       ↓
Incident created/updated
       ↓
IncidentCreated / IncidentUpdated
```

### Important design choice

Incident correlation should remain owned by:

```
```

```
anomaly_service
```

because the audit already identifies the anomaly service as the owner of incident correlation.

We don't create an `incident_service` just for the sake of architectural purity.

---

# 8. Incident → Root Cause

Current:

```
```

```
POST /root-causes
    +
incident_id
```

and Root Cause directly reads anomaly/incident tables. 

Target:

```
```

```
IncidentCreated
       ↓
Root Cause consumer
       ↓
Root Cause engine
       ↓
RootCause persisted
```

Event:

```
```

```
IncidentReadyForRootCause
```

or simply:

```
```

```
IncidentCreated
```

### Which one?

I recommend **not creating artificial events for every internal operation**.

Use domain events only where another capability genuinely reacts.

So:

```
```

```
IncidentCreated
       ↓
Root Cause
```

is sufficient for the prototype.

---

# 9. Root Cause → Business Impact

Same pattern.

Current:

```
```

```
POST /business-impact
```

with direct DB reads from Incident/Root Cause. 

Target:

```
```

```
RootCauseCompleted
       ↓
Business Impact
       ↓
BusinessImpactAssessment persisted
```

Again:

```
```

```
incident_id
root_cause_id
```

remain explicit lineage fields.

The database already stores these relationships as plain columns with DB-level FKs. 

---

# 10. Business Impact → Recommendation

This is the **first broken connection we absolutely need to fix.**

The intended design already exists:

```
```

```
BusinessImpactCompleted
       ↓
Recommendation consumer
```

But:

> `business_impact_service` currently publishes nothing.

The consumer endpoint exists, but nothing in production calls it. 

### Target

```
```

```
Business Impact completed
        │
        ▼
BusinessImpactCompleted
        │
        ├───────────────┐
        ▼               ▼
Recommendation      Evaluation
```

This is the correct fan-out.

---

# 11. Business Impact → Evaluation

Same event.

The evaluation service already consumes the same `BusinessImpactCompleted` event. 

Therefore:

```
```

```
BusinessImpactCompleted
       │
       ├──► Recommendation
       │
       └──► Evaluation
```

### Not:

```
```

```
Business Impact
      ↓
Recommendation
      ↓
Evaluation
```

The latter would unnecessarily make Evaluation depend on Recommendation.

The repository's actual architecture already indicates **parallel fan-out**. 

So we keep that.

---

# 12. Recommendation → Evaluation

This is another important correction.

There is a `RecommendationsGenerated` publisher, but it is effectively log-only and has **zero consumers**. Evaluation is currently triggered directly from Business Impact instead. 

Therefore:

```
```

```
BusinessImpactCompleted
      ├──────────────► Recommendation
      │
      └──────────────► Evaluation
```

is the target.

We **do not create**:

```
```

```
RecommendationGenerated
        ↓
Evaluation
```

unless a future product requirement actually says evaluation is specifically an evaluation *of the generated recommendation*.

For the current architecture, that would add unnecessary coupling.

---

# 13. Human Action / Outcome

This remains outside Step 7.

Current:

```
```

```
Recommendation
      ↓
Human Action
      ↓
Outcome
      ↓
Organizational Knowledge
```

does not exist in the repository at all. 

So:

```
```

```
Recommendation
      ↓
[STEP 7 STOPS HERE]
```

No fake tables.

No fake lifecycle API.

No fake outcome metrics.

---

# 14. Cross-service communication strategy

Now the big architectural decision.

The repository currently has:

```
```

```
Frontend
   ↓
Gateway
   ↓
[no real downstream HTTP]
```

and backend services have:

```
```

```
Service A
   ↓
shared PostgreSQL
   ↓
Service B
```

There are **no genuine HTTP calls between backend services** and no real message broker. 

## Our target should be:

```
```

```
Frontend
   ↓ HTTP
Gateway
   ↓ HTTP
Backend APIs

Backend domain transitions
   ↓
Event abstraction
   ↓
Consumers
```

So we separate:

### Synchronous communication

Used for:

```
```

```
Frontend → Gateway
Gateway → service
```

### Event communication

Used for:

```
```

```
Domain event → downstream processing
```

This is a much cleaner boundary.

---

# 15. Do NOT add Kafka yet

The audit confirms there is currently:

-  no Kafka 
-  no RabbitMQ 
-  no Redis broker 
-  no scheduler 
-  no Celery/APScheduler 

and the current event implementation is an in-process/log-only stand-in. 

For this prototype, adding Kafka would introduce infrastructure complexity without giving us meaningful product value.

So:

```
```

```
Step 7
   ↓
Event abstraction
   ↓
In-process implementation
```

Later:

```
```

```
Production evolution
   ↓
Real broker
```

This aligns with the project's existing principle that infrastructure complexity should only be introduced when justified by system behavior. 

---

# 16. Idempotency

This part of the existing architecture is actually good.

Both:

```
```

```
recommendation_generations.event_id
evaluations.event_id
```

have unique constraints, plus application-level fast-path checks. 

So our rule becomes:

> **Every event consumer that creates a persistent downstream artifact must be idempotent.**

Example:

```
```

```
BusinessImpactCompleted
event_id = ABC123
```

Recommendation receives it:

```
```

```
Does ABC123 already exist?
     │
   YES → return existing result
     │
    NO
     ↓
Generate recommendation
     ↓
Persist event_id = ABC123
```

The database UNIQUE constraint remains the final concurrency backstop.

---

# 17. Failure behavior

We should formalize this now.

### Malformed event

```
```

```
→ reject
→ don't process
→ don't retry
```

The existing consumers already treat malformed/duplicate events as non-retryable 2xx/202 outcomes. 

### Processing exception

```
```

```
→ 5xx / failure
→ eligible for future retry
```

That is already the documented intended behavior.

### But currently...

There is no broker, so nothing actually retries the event. 

Therefore:

**Step 7 prototype:** preserve the semantics.

**Production phase:** add actual retry infrastructure.

---

# 18. The Outbox question

The audit also found a prototype-stage gap around event publication after DB commits. Recommendation's event publisher can fail after the DB operation and there is no Outbox Pattern. 

Should we add Outbox now?

### My recommendation: No.

For the prototype:

```
```

```
DB transaction
     ↓
in-process event publication
```

is sufficient.

But document:

```
```

```
Outbox Pattern = production hardening
```

because once we move to a real broker, we need reliable:

```
```

```
DB commit
+
event publication
```

without losing events.

---

# 19. What about the direct DB reads?

This is the biggest architectural compromise.

Current:

```
```

```
anomaly_service
     ↓
complaints
complaint_enrichments

root_cause_service
     ↓
incidents
active_anomalies
incident_anomalies

business_impact_service
     ↓
incidents
active_anomalies
incident_anomalies
root_causes
```

The audit confirms all of these are read-only but still violate service data ownership. 

## We should NOT rewrite them in Batch 3.

Instead, classify them:

> **Existing prototype coupling — accepted temporarily, explicitly documented as technical debt.**

Why?

Because replacing all of them with service APIs/events would require:

```
```

```
API contracts
DTOs
new HTTP clients
failure handling
timeouts
retries
possibly read models
migration of repositories
test rewrites
```

That is a separate architecture migration.

---

# 20. But we need a future boundary

The target evolution should be:

```
```

```
CURRENT

Service A
   ↓
PostgreSQL
   ↓
Service B


TARGET

Service A
   │
   └── Event/API
          ↓
       Service B
```

So the database read-models become **migration seams**, not permanent architecture.

We'll document:

```
```

```
DATA-002
Current prototype compatibility mechanism
        ↓
Future replacement
API/event-based integration
```

---

# 21. Partial failure in Gateway aggregation

This matters a lot because Dashboard and Investigation aggregate multiple services.

Imagine:

```
```

```
Dashboard
 ├── incidents        ✓
 ├── recommendations  ✓
 ├── business impact  ✗
 └── trends           ✓
```

We should **not turn the entire Dashboard into a 500**.

The frontend architecture already emphasizes section-level isolation and skeleton/loading behavior. 

So the Gateway contract should support:

```
```

```
DashboardResponse
├── operationalBrief: data
├── decisionSummary: data
├── investigationEntryPoints: partial/error
└── supportingEvidence: deferred
```

Meaning:

> **Aggregation failures should be represented at the section/data-source boundary whenever possible.**

Not:

```
```

```
one downstream failure
      ↓
whole application unavailable
```

---

# 22. Timeout strategy

We also need a simple rule.

For Gateway → downstream calls:

```
```

```
request
   ↓
bounded timeout
   ↓
success → aggregate
failure → section degradation
```

We do **not** allow:

```
```

```
Gateway
 ↓
Service A waits
 ↓
Service B waits
 ↓
Service C waits
 ↓
Service D waits
 ↓
Frontend hangs
```

The audit specifically identified synchronous chains, timeout propagation, retry amplification and expensive aggregation as risks to consider. 

Exact timeout values belong in implementation/configuration, not architecture.

---

# 23. Frontend should never orchestrate the pipeline

This is a hard rule.

The frontend should **never do**:

```
```

```
POST /enrichment
POST /anomaly
POST /incident
POST /root-cause
POST /business-impact
POST /recommendation
```

just to populate a workspace.

Instead:

```
```

```
Frontend
    ↓
Gateway
    ↓
read/query APIs
```

The pipeline itself is backend-owned.

This keeps the UI from becoming an accidental workflow engine.

---

# 24. Target architecture

So the full target now looks like this:

```
```

```
                         FRONTEND
                            │
                            │ HTTP
                            ▼
                       API GATEWAY
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
        Workspace       Workspace      Workspace
          APIs             APIs           APIs
             │              │              │
             └──────────────┼──────────────┘
                            │
                     DOMAIN SERVICES
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
   Ingestion              NLP                Anomaly
       │                    │                    │
       └────────────── EVENT FLOW ──────────────┘
                            │
                            ▼
                         Incident
                            │
                     ┌──────┴──────┐
                     ▼             ▼
                 Root Cause   [future/other]
                     │
                     ▼
                Business Impact
                     │
              ┌──────┴──────┐
              ▼             ▼
       Recommendation    Evaluation
              │             │
              └──────┬──────┘
                     ▼
                PostgreSQL
```

And separately:

```
```

```
Recommendation
      ↓
Human Action
      ↓
Outcome
      ↓
Organizational Knowledge

       FUTURE
```

---

# 25. What we are actually fixing in Step 7

This is the crucial scope boundary.

### **Must fix**

1.  Gateway routing 
2.  Frontend → Gateway connectivity 
3.  CORS 
4.  API client 
5.  Workspace aggregation 
6.  Real workspace data flow 
7.  BusinessImpactCompleted publisher 
8.  Recommendation/Evaluation event consumption 
9.  Event contract 
10.  Idempotency preservation 
11.  Pipeline observability/state visibility 
12.  Partial aggregation failure handling 

These are directly blocking real integration. The audit explicitly classifies Gateway, auth, CORS, frontend API infrastructure and aggregation decisions as P0 integration concerns. 

### **Do NOT rewrite now**

1.  Shared database architecture 
2.  DATA-002 read models 
3.  Introduce Kafka 
4.  Outbox 
5.  Full retry infrastructure 
6.  Human Action 
7.  Outcome tracking 
8.  Organizational Knowledge 
9.  Copilot 
10.  Full Administration platform 

Those are separate capabilities or production-hardening concerns.

---

# 26. One thing we need to settle before implementation

There is one remaining architectural question from Batch 3:

### Authentication

The audit confirms **zero authentication/authorization exists anywhere**. There are no auth settings, auth service, JWT/OAuth implementation, or roles/permissions. 

But our roadmap places JWT/RBAC in Phase 13. 

So I would freeze the decision as:

> **Step 7 defines the authentication boundary and ensures the Gateway is the enforcement point, but full JWT/RBAC implementation remains Phase 13 unless we explicitly promote it into Step 7.**

That keeps the roadmap internally consistent.

---

## Batch 3 result

We now have the core integration doctrine:

**Synchronous API**
 → Frontend ↔ Gateway ↔ backend services

**Event-driven pipeline**
 → domain transition ↔ downstream processing

**`incident_id`**
 → business lineage

**`event_id`**
 → event idempotency

**Gateway**
 → aggregation/orchestration, not domain intelligence

**Services**
 → own their domain logic

**Current shared DB reads**
 → accepted prototype technical debt, not expanded

**In-process events**
 → prototype implementation

**Real broker + Outbox + retries**
 → future production evolution

**Human Action / Outcome**
 → explicitly future

And the most important broken production-path issue is now clear:

```
```

```
Business Impact
      │
      ▼
BusinessImpactCompleted
      │
      ├──────────► Recommendation
      │
      └──────────► Evaluation
```

The event contract exists conceptually and both consumers exist, but **the publisher is missing**.