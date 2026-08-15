# Evaluation Service

**Port:** 8008

An independent, out-of-band intelligence-assurance observer. Consumes `BusinessImpactCompleted` events and computes quality/explainability scores over the pipeline's own output — it is never a blocking step in the operational pipeline and never modifies any upstream service. Its output is not currently surfaced by any Gateway route, dashboard, or Copilot tool (a known, tracked gap — see the root README's Known Limitations).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |
| GET | /api/v1/evaluations | List evaluations |
| GET | /api/v1/evaluations/{id} | Get an evaluation by id |
| GET | /api/v1/evaluations/latest/{incident_id} | Latest evaluation for an incident |
| POST | /internal/events/business-impact-completed | Internal event receiver (requires `X-Internal-Secret`) |

## Local Development

```bash
docker compose up evaluation_service
```

## Environment Variables

See root [`.env.example`](../../../.env.example) for all configuration options.
