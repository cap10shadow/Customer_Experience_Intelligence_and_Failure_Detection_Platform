# Recommendation Service

**Port:** 8006

Responsible for generating operational recommendations, prioritizing mitigation
actions, and suggesting escalation paths based on intelligence outputs.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |

## Local Development

```bash
docker compose up recommendation_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
