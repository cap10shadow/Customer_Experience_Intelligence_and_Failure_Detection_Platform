# Copilot Service

**Port:** 8007

Responsible for AI-powered natural-language querying, operational summaries,
executive explanations, and tool-calling orchestration for investigation workflows.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |

## Local Development

```bash
docker compose up copilot_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
