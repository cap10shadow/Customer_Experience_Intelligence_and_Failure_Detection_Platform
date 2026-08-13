# Copilot Service

**Port:** 8007

Responsible for AI-powered natural-language querying, operational summaries,
executive explanations, and tool-calling orchestration for investigation workflows.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |
| POST | /api/v1/copilot/messages | Internal-only (reachable from gateway_service, never the public internet). Phase 12 Batch 1: no tool/LLM logic yet -- always returns an honest placeholder response. See `docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md`. |

## Local Development

```bash
docker compose up copilot_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
