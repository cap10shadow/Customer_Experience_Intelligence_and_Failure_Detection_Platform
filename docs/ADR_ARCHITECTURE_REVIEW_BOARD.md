
# ARCHITECTURE DECISION RECORD — ARCHITECTURE REVIEW BOARD (ARB)

**Project:** Customer Experience Intelligence & Failure Detection Platform

**Session Date:** 2026-07-24

**Status:** Approved — Finalized

---

## 1. Purpose

This document records the outcome of the Architecture Review Board (ARB) session convened to evaluate the platform's complete product vision and long-term architecture, independent of current implementation status.

Its purpose is to:

- formally ratify the platform's identity and long-term direction
- resolve terminology and conceptual inconsistencies identified across the documentation set
- clarify architectural principles that were implicit but never explicitly written down
- establish a long-term evolution vision without changing MVP scope or any completed engineering work

This document is the authoritative record of the ARB's conclusions. All other project documents have been aligned to it. Where any other document appears to conflict with this record, **this document governs**.

---

## 2. Context

Prior to this session, the platform's architecture had been reviewed end-to-end as if evaluating the product before a large engineering team committed further effort. That review surfaced a small number of unresolved questions that recurred across multiple documents without ever being formally decided:

- Was the platform's identity a complaint-analytics dashboard, or something larger?
- Should the intelligence pipeline remain a one-way flow, or evolve into a closed feedback loop?
- Should the Business Impact Engine's scoring adapt per organization, or remain generic?
- How should users explore business impact without changing the underlying engine?
- Should the platform track organizational learning over time?
- How should "evidence" and "confidence" be understood across stages that each produce their own explanations and their own confidence signals?
- Should Root Cause and Business Impact analysis introduce a new "Case" entity, or reuse the existing Incident?

These questions were debated by the ARB and resolved into the eight decisions recorded below. None of them alter any already-completed phase, any frozen engine (Root Cause Rule Engine, Business Impact Analysis Engine), or any persisted schema. All of them are either (a) clarifications of principles that were already implicit in the approved ADRs (DATA-002, RCA-001, BI-001 through BI-006), or (b) long-term vision statements explicitly scoped as post-MVP.

---

## 3. Review Summary

The ARB concluded that the platform's core engineering — the deterministic, explainable intelligence pipeline from Complaint through Business Impact — is sound and requires no redesign. Two categories of change were approved:

1. **Clarifications** (ADR-003, ADR-004, ADR-007, ADR-008) — making explicit what was already true in practice, so future engineers and documentation do not drift from it.
2. **Long-term vision** (ADR-002, ADR-005, ADR-006) — extending the documented *destination* of the platform without changing the *current* MVP roadmap or scope.

One identity clarification (ADR-001) was ratified to give the platform a name that reflects both what it already does and what it is becoming.

No new services, no schema changes, and no MVP scope changes resulted from this session.

---

## 4. Approved Architectural Decisions

### ADR-001 — Platform Identity

**Decision:** The platform is a **Customer Experience Intelligence & Operational Decision Support Platform**. Its purpose is to transform customer complaints into explainable operational intelligence and evidence-based business decisions. The platform is **not** merely a complaint analytics dashboard.

**Rationale:** Every prior document already described this identity in spirit — the platform was never scoped as a passive analytics dashboard, and its non-goals (PRD.md §5, §7) explicitly reject "basic dashboarding" and "generic chatbot" framing. This decision simply gives that identity a formal, citable name so it can be referenced consistently across all documentation.

---

### ADR-002 — Intelligence Lifecycle

**Decision:** The platform evolves from a one-way intelligence pipeline into a complete intelligence lifecycle.

Current flow (MVP and near-term roadmap, unchanged):

```
Complaint → NLP → Anomaly → Incident → Root Cause → Business Impact → Recommendation
```

Long-term evolution (post-MVP vision, not a roadmap commitment):

```
Complaint → NLP → Anomaly → Incident → Root Cause → Business Impact → Recommendation
    → Human Action → Outcome → Organizational Knowledge → Continuous Improvement → AI Copilot
```

**Rationale:** A pipeline that terminates at "Recommendation" and "Dashboard" can never learn whether its conclusions were correct or its recommendations effective — every confidence score and severity band would remain permanently self-referential. Extending the documented long-term vision to include what happens *after* a recommendation (a human acts on it, an outcome results, that outcome becomes organizational knowledge, and that knowledge continuously improves future intelligence) closes this loop conceptually. **This is a long-term architectural vision. It is explicitly not part of the MVP** and does not change any current phase, deliverable, or exit criterion.

---

### ADR-003 — Business Impact Engine

**Decision:** The Business Impact Engine remains:

- deterministic
- explainable
- rule-based
- generic

The engine always evaluates every Business Impact dimension (Financial, Customer, Operational, SLA, Reputation). No dimensions are disabled. No organization-specific scoring logic is introduced. The engine produces one authoritative Business Impact Assessment.

**Rationale:** This ratifies and reinforces BI-001 through BI-006 exactly as already frozen — it introduces no new behavior. Its purpose is to foreclose a specific risk identified during review: as the platform is positioned for multiple industries with different priorities (PROJECT_BRAIN.md §6), it would be tempting to let the engine itself branch per organization (different weights, different rules, different dimensions per industry). The ARB explicitly rejects this. The engine stays universal and generic; any future need for organization-specific emphasis is addressed at the presentation layer (ADR-004), never inside the engine.

---

### ADR-004 — Presentation Layer

**Decision:** Instead of changing Business Impact calculations, the Presentation Layer (Dashboard and AI Copilot) allows users to explore specific dimensions, compare dimensions, request business-specific explanations, and focus on Financial, Customer, Operational, SLA, Reputation, or other dimensions as needed. The Presentation Layer adapts the **explanation**, not the **engine**. Business reasoning remains consistent for every organization and every user.

**Rationale:** This is the architectural resolution to the same risk ADR-003 forecloses from the other direction. Different organizations and different personas (Executive vs. Reliability Engineer vs. Business Analyst — PRD.md §3) legitimately care about different dimensions of the same assessment. Rather than making the engine aware of "who is asking" — which would compromise its determinism and generality — the presentation layer is responsible for selecting, filtering, comparing, and re-narrating an already-computed, already-authoritative assessment. The underlying numbers never change based on who is looking at them; only what is surfaced and how it is explained does.

---

### ADR-005 — Organizational Knowledge

**Decision:** The platform should preserve organizational knowledge. Future phases should support learning from Human Actions, Outcomes, Historical Incidents, and Previous Recommendations. This enables continuous organizational learning.

**Rationale:** This is the substantive content behind the "Organizational Knowledge" and "Continuous Improvement" stages of ADR-002's long-term lifecycle. It formally acknowledges — without committing to a schema, service, or MVP deliverable — that the platform's long-term value depends on remembering what happened previously and using that memory to inform future intelligence, rather than evaluating every incident as if it were the first of its kind. This is long-term vision only; no current phase, entity, or persisted schema is affected.

---

### ADR-006 — Evidence Chain

**Decision:** Every intelligence stage contributes evidence. The platform should conceptually maintain a connected evidence chain across:

```
Complaint → NLP → Anomaly → Incident → Root Cause → Business Impact → Recommendation
```

This is a **conceptual** architecture decision, not an implementation requirement.

**Rationale:** Each stage already produces its own explainable output (NLP enrichment fields, anomaly explanations, Root Cause `Evidence` objects, Business Impact `ImpactEvaluation` reasons). This decision formally names the *idea* that these are not independent explanations but segments of one continuous evidentiary trail belonging to a single operational story. Naming this conceptually — without prescribing a shared schema, a new table, or a new service — preserves every service's autonomy over its own explanation format (consistent with DATA-002) while giving future explainability and AI-copilot work a documented principle to build toward.

---

### ADR-007 — Incident Lifecycle

**Decision:** A separate "Case" entity will **not** be introduced. Instead, **Incident** naturally evolves into the central lifecycle object connecting:

```
Anomalies → Root Cause → Business Impact → Recommendation → Human Action → Outcome → Organizational Knowledge
```

**Rationale:** Incident already plays this role in practice — it is the object the Incident Correlation Engine (Phase 5 Step 3, INCIDENT-001) produces, the object Root Cause Analysis consumes (RCA-001), and the object Business Impact Analysis is computed for (Phase 7). Introducing a new, parallel "Case" concept would duplicate an entity that already exists and already sits at the center of the pipeline. The ARB rejects that duplication: Incident *is* the platform's central lifecycle object, today and in the long-term vision, and every future stage (Recommendation, Human Action, Outcome, Organizational Knowledge) is understood to attach to the Incident it originated from.

---

### ADR-008 — Confidence

**Decision:** Confidence remains stage-specific. Each service owns its own confidence definition. The architecture clarifies this explicitly. It does **not** force one universal confidence score.

**Rationale:** Review found that "confidence" is used across the platform to mean genuinely different things — NLP classification confidence, anomaly severity (a magnitude-based proxy), Root Cause's `confidence_score`/`confidence_level` (certainty that the correct rule fired), and Business Impact's `confidence` (completeness of available input data, not certainty of correctness). Forcing these into one universal scale would either lose meaning or misrepresent what each stage is actually measuring. The ARB decision is to stop treating this as an unresolved inconsistency and instead formally document it as intentional: confidence is, and should remain, a stage-owned concept, defined and interpreted in the context of what that stage actually does.

---

## 5. Architectural Rationale

Taken together, these eight decisions do not change a single engine, schema, or MVP deliverable. They accomplish three things:

1. **They name the platform's identity and long-term destination** (ADR-001, ADR-002, ADR-005), giving every current phase a documented endpoint to build toward without requiring that endpoint to exist yet.
2. **They draw a firm boundary between the engine and its presentation** (ADR-003, ADR-004), protecting the determinism and universality of the Business Impact Engine — and, by extension, every future deterministic engine built the same way — from being eroded by legitimate but dangerous pressure to "just make it configurable per customer" inside the engine itself.
3. **They resolve terminology that was previously ambiguous by declaring it intentional rather than defective** (ADR-006, ADR-007, ADR-008) — evidence, Incident, and confidence are not inconsistencies to be fixed; they are deliberate architectural choices to be documented clearly so they are never "fixed" into something worse.

---

## 6. Long-Term Vision

The finished platform, per this ARB session, is not a smarter dashboard. It is a system that:

- turns customer complaints into a fully explainable chain of evidence, from raw signal to business consequence (ADR-006), anchored at every step to the Incident that chain belongs to (ADR-007);
- produces one deterministic, generic, trustworthy Business Impact Assessment per incident, regardless of which organization or industry is asking (ADR-003), while letting every user explore that same assessment through the lens that matters to them (ADR-004);
- eventually remembers what actions were taken and what happened as a result, so that organizational knowledge accumulates rather than resetting with every new incident (ADR-005), closing the loop from signal to decision to outcome and back (ADR-002);
- and expresses confidence honestly, at the level each stage actually understands it, rather than manufacturing a false sense of unified certainty (ADR-008).

This vision does not require, and does not authorize, any change to the current MVP roadmap, the frozen Root Cause or Business Impact engines, or any completed phase. It is the direction those phases are already heading, now written down.
