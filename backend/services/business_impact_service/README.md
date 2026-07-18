# Business Impact Service

**Port:** 8005

Responsible for estimating churn risk, calculating severity scores, estimating
operational and business impact, and prioritizing incidents by risk level.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |

## Local Development

```bash
docker compose up business_impact_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
