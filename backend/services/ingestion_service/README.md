# Ingestion Service

**Port:** 8001

Responsible for ingesting customer complaints and operational signals, validating
incoming data, and normalizing records into structured complaint events.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |

## Local Development

```bash
docker compose up ingestion_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
