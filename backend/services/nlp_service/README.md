# NLP Service

**Port:** 8002

Responsible for complaint classification, urgency detection, sentiment analysis,
issue extraction, and complaint enrichment into structured intelligence records.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |

## Local Development

```bash
docker compose up nlp_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
