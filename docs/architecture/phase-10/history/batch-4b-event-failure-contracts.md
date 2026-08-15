Yep. **Batch 4B starts now.** We’ll keep it focused on the event contracts and failure behavior, then freeze it before moving on.

# Batch 4B — Event & Failure Contracts

The current audit shows that the backend has the *shape* of an event-driven pipeline, but the actual production wiring is incomplete: `BusinessImpactCompleted` consumers exist in Recommendation and Evaluation, while Business Impact does not actually publish the event. 

So our job here is to define the **target contract**, not pretend the current implementation is already there.

---

## 4B-1. Event Contract

We have three relevant lifecycle events.

### Event 1 — `BusinessImpactCompleted`

This is the key fan-out event.

```
```

```
{
  "eventId": "UUID",
  "eventType": "BusinessImpactCompleted",
  "eventVersion": "1.0",
  "occurredAt": "ISO-8601 UTC",
  "source": "business_impact_service",
  "correlationId": "incident-id",
  "payload": {
    "incidentId": "UUID",
    "businessImpactAssessmentId": "UUID",
    "rootCauseId": "UUID",
    "impactSeverity": "string",
    "impactPriority": "string",
    "dimensions": [],
    "confidence": "string"
  }
}
```

### Why these metadata fields?

```
```

```
eventId
```

Unique event identity → idempotency.

```
```

```
eventType
```

Allows consumers to identify the event.

```
```

```
eventVersion
```

Allows the contract to evolve without silently breaking consumers.

```
```

```
occurredAt
```

Event timestamp.

```
```

```
source
```

Identifies the producer.

```
```

```
correlationId
```

Keeps the entire Incident → Root Cause → Impact → Recommendation/Evaluation chain traceable.

The current system already has `event_id` uniqueness as an idempotency mechanism in Recommendation and Evaluation, so this formalizes something the code already partially does. 

---

# 4B-2. Consumers

`BusinessImpactCompleted` has **two consumers**:

```
```

```
                    ┌──→ recommendation_service
                    │
business_impact ────┤
                    │
                    └──→ evaluation_service
```

Not:

```
```

```
Business Impact
      ↓
Recommendation
      ↓
Evaluation
```

The audit explicitly confirms that Evaluation consumes the same `BusinessImpactCompleted` event independently; it is a parallel fan-out. 

So we freeze:

> **Recommendation and Evaluation are independent consumers of BusinessImpactCompleted.**

---

# 4B-3. Recommendation Event

After Recommendation completes:

```
```

```
{
  "eventId": "UUID",
  "eventType": "RecommendationsGenerated",
  "eventVersion": "1.0",
  "occurredAt": "ISO-8601 UTC",
  "source": "recommendation_service",
  "correlationId": "incident-id",
  "payload": {
    "incidentId": "UUID",
    "generationId": "UUID",
    "recommendationIds": ["UUID"],
    "recommendationCount": 0
  }
}
```

However, **this event is not currently consumed anywhere**.

The audit confirms the existing publisher is only an in-process/logging publisher and no consumer exists. 

Therefore:

```
```

```
RecommendationsGenerated
        ↓
     emitted
        ↓
   no consumer
```

is currently acceptable for the prototype.

We do **not** invent an Evaluation dependency on this event.

---

# 4B-4. Evaluation Event

```
```

```
{
  "eventId": "UUID",
  "eventType": "EvaluationCompleted",
  "eventVersion": "1.0",
  "occurredAt": "ISO-8601 UTC",
  "source": "evaluation_service",
  "correlationId": "incident-id",
  "payload": {
    "incidentId": "UUID",
    "evaluationId": "UUID",
    "overallStatus": "string",
    "confidence": "string"
  }
}
```

This is currently the terminal event.

The audit confirms nothing consumes `EvaluationCompleted`. 

So:

```
```

```
EvaluationCompleted
        ↓
      END
```

for this prototype.

---

# 4B-5. Event Flow — Frozen

The target event architecture is:

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
Root Cause
   │
   ▼
Business Impact
   │
   │
   └────────────── BusinessImpactCompleted ──────────────┐
                                                        │
                              ┌─────────────────────────┴────────────────────┐
                              ▼                                              ▼
                    Recommendation Service                         Evaluation Service
                              │                                              │
                              ▼                                              ▼
                   RecommendationsGenerated                       EvaluationCompleted
                              │                                              │
                              ▼                                              ▼
                             END                                            END
```

This reflects the actual intended topology much more accurately than a sequential Recommendation → Evaluation pipeline. 

---

# 4B-6. Delivery Semantics

Now we freeze how events behave.

### At-least-once delivery

For the prototype:

> **Events are at-least-once, not exactly-once.**

Meaning a consumer may receive the same event more than once.

Therefore consumers **must be idempotent**.

This aligns with the existing Recommendation/Evaluation implementation, which already checks `event_id` and has DB uniqueness constraints as a duplicate-event backstop. 

---

## Duplicate event

Example:

```
```

```
eventId = abc-123

Recommendation receives abc-123
→ processes
→ commits

abc-123 arrives again
→ detect existing event
→ DO NOT generate another recommendation
```

Target result:

```
```

```
{
  "outcome": "DUPLICATE",
  "eventId": "abc-123"
}
```

We don't need to expose this exact internal response through the public Gateway.

---

# 4B-7. Retry Semantics

Freeze:

```
```

```
Transient failure
        ↓
retry
        ↓
success → completed
        ↓
persistent failure → failed/dead-letter
```

Retry-worthy:

```
```

```
connection failure
timeout
temporary downstream unavailable
temporary database failure
```

Not retry-worthy:

```
```

```
malformed event
invalid schema
missing required identifier
unsupported event version
business-rule rejection
```

The current Recommendation implementation already treats malformed payloads as rejected and unhandled lifecycle failures as 5xx, while noting that a real broker would retry. 

---

# 4B-8. Outbox

This is an important architecture decision.

The audit explicitly identifies the absence of an Outbox Pattern as a current prototype-stage gap. 

For **this prototype**, freeze:

> **Outbox is not required for Step 7 integration.**

But the architecture must leave room for it.

So:

```
```

```
Business Impact transaction
        ↓
DB commit
        ↓
publish event
```

is acceptable for the prototype.

Production-grade future:

```
```

```
DB transaction
   ├── business data
   └── outbox event
          ↓
      publisher
          ↓
       broker
```

We don't build the production broker/outbox now unless the intermediate Step 7.x scope specifically requires it.

---

# 4B-9. API Failure Semantics

Now the Gateway side.

Freeze these meanings:

| StatusMeaning |                                                              |
| ------------- | ------------------------------------------------------------ |
| `400`         | Malformed request                                            |
| `401`         | Authentication required/invalid — **future auth capability** |
| `403`         | Authenticated but unauthorized — **future auth capability**  |
| `404`         | Entity/resource doesn't exist                                |
| `409`         | Valid request conflicts with current state                   |
| `422`         | Validation failure                                           |
| `429`         | Rate limit — future/optional                                 |
| `500`         | Unexpected internal failure                                  |
| `502`         | Downstream service failure                                   |
| `503`         | Service unavailable                                          |
| `504`         | Downstream timeout                                           |

The distinction between `500`, `502`, `503`, and `504` is important once the Gateway actually starts aggregating downstream services.

---

# 4B-10. Gateway Error Envelope

Freeze one common public error shape:

```
```

```
{
  "error": {
    "code": "DOWNSTREAM_SERVICE_UNAVAILABLE",
    "message": "The investigation data could not be retrieved.",
    "requestId": "UUID",
    "details": null
  }
}
```

Fields:

```
```

```
code
message
requestId
details
```

### `code`

Machine-readable.

Examples:

```
```

```
VALIDATION_ERROR
RESOURCE_NOT_FOUND
CONFLICT
DOWNSTREAM_SERVICE_UNAVAILABLE
DOWNSTREAM_TIMEOUT
INTERNAL_ERROR
```

### `message`

Human-readable but safe.

### `requestId`

Allows tracing a frontend failure through Gateway/backend logs.

### `details`

Optional structured information.

Never expose:

```
```

```
stack traces
SQL errors
database credentials
internal hostnames
raw exception objects
```

---

# 4B-11. Aggregation Failure

This matters particularly for Investigation.

Suppose:

```
```

```
GET /investigations/{incidentId}

Incident       ✓
Evidence       ✓
Root Cause     ✓
Business Impact ✗
Recommendation ✗
```

We should **not silently return fabricated empty data**.

For Step 7:

> The Gateway should distinguish **missing data** from **failed downstream retrieval**.

Target response:

```
```

```
{
  "error": {
    "code": "DOWNSTREAM_SERVICE_UNAVAILABLE",
    "message": "Investigation data is temporarily unavailable.",
    "requestId": "..."
  }
}
```

Later, if we deliberately choose partial-response semantics, that becomes an explicit architecture decision.

For now:

**fail the aggregate rather than silently producing a misleading investigation.**

---

# 4B-12. Event vs API Responsibilities

This distinction is now frozen.

### APIs

Used for:

```
```

```
Frontend → Gateway
Gateway → services
User-driven reads
User-driven commands
```

### Events

Used for:

```
```

```
Service → Service
Pipeline progression
Asynchronous processing
Fan-out
Lifecycle notifications
```

Therefore:

```
```

```
Frontend
   ❌ directly consumes events

Frontend
   ↓
Gateway API
   ↓
service
```

And:

```
```

```
Service
   ↓
Event
   ↓
Consumer service
```

---

# 4B-13. What is actually missing?

This is where your new intermediate step becomes useful.

From the audit:

### Already exists

```
```

```
BusinessImpactCompleted consumers
Recommendation lifecycle
Evaluation lifecycle
event_id idempotency
RecommendationsGenerated publisher abstraction
EvaluationCompleted publisher abstraction
```

### Missing

```
```

```
BusinessImpactCompleted producer
Actual event transport
Actual broker/messaging infrastructure
Cross-service event delivery
Outbox
Dead-letter mechanism
Production retry infrastructure
```

The audit explicitly confirms there is **no messaging infrastructure at all** and no Business Impact publisher. 

So we **do not pretend Batch 4B means "implement Kafka/RabbitMQ now."**

---

# Batch 4B Final Architecture Decision

### Prototype

```
```

```
                REST
Frontend ───────────────→ Gateway
                            │
                            ├──→ service APIs
                            │
                            └──→ aggregation
                            
Service pipeline
       │
       ▼
  Event abstraction
       │
       ▼
 In-process transport
       │
       ├──→ Recommendation
       └──→ Evaluation
```

### Production evolution

```
```

```
Services
   │
   ▼
Outbox
   │
   ▼
Message Broker
   │
   ├──→ Recommendation
   └──→ Evaluation
```

---

## 4B is now frozen