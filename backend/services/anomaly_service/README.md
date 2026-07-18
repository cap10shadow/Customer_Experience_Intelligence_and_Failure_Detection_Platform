# Anomaly Service

**Port:** 8003

Responsible for complaint spike detection, trend analysis, anomaly monitoring,
and regional issue tracking across operational data streams.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |

## Local Development

```bash
docker compose up anomaly_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
