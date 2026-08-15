# Phase 10 — Working Architecture History

These six documents are the raw, batch-by-batch working drafts that established the frontend/backend integration architecture later formalized in `STEP_7X_IMPLEMENTATION_ARCHITECTURE.md`, `STEP_7X_SCOPE_FREEZE.md`, and `STEP_7X_CAPABILITY_GAP_INVENTORY.md` (one directory up). They are kept for the architectural reasoning they contain — why the integration boundary was drawn where it was, what alternatives were considered for event/failure contracts, and how each batch's decisions were validated against the running system — not as active reference documentation.

For the current, authoritative description of this architecture, use the Step 7.X documents one directory up, or `docs/DECISIONS.md`.

| File | Covers |
|---|---|
| `batch-1-integration-foundation-architecture.md` | The technical boundary between the existing frontend and backend |
| `batch-2-workspace-api-backend-integration.md` | Per-workspace data path, including intentionally-deferred capabilities |
| `batch-3-cross-service-pipeline-communication.md` | Target cross-service pipeline shape |
| `batch-4a-api-data-contract-architecture.md` | API/data contract boundary |
| `batch-4b-event-failure-contracts.md` | Event and failure-handling contracts (`BusinessImpactCompleted` wiring) |
| `batch-4c-integration-readiness-pass.md` | Final Frontend → API → Gateway → Backend → Persistence trace, batch-by-batch |
