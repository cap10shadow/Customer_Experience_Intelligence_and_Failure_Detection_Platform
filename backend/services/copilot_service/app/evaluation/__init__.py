"""
Phase 12 Batch 6 -- the Copilot agent-evaluation harness (architecture
§26, `docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md`).

Owned entirely by `copilot_service` -- conceptually
`backend/services/copilot_service/app/evaluation/`, exactly the
structural placeholder §26 names. This package has no dependency on,
and is never imported by, `evaluation_service` (Phase 8) -- see §25 of
the architecture and `docs/DECISIONS.md`'s COPILOT-001/002. It evaluates
agent *behavior* (tool selection, grounding, hallucination, conflict
disclosure, safety, completeness), never domain intelligence quality,
which remains `evaluation_service`'s independent concern.

This is a developer-facing, internal capability only: no Gateway route,
no frontend surface, no new database table. Run it via
`python -m backend.services.copilot_service.app.evaluation`.
"""
