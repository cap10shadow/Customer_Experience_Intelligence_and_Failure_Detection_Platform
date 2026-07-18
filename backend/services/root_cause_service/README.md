# Root Cause Service

**Port:** 8004

Responsible for correlating complaints with operational signals, estimating
probable root causes, and identifying issue dependencies.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |

## Local Development

```bash
docker compose up root_cause_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
