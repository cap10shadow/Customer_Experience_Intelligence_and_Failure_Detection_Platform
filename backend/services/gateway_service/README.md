# Gateway Service

**Port:** 8000

Entry point for all client and frontend requests. Responsible for API routing,
authentication, and orchestration of requests to downstream intelligence services.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |

## Local Development

```bash
docker compose up gateway_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
