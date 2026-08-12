from pydantic_settings import BaseSettings, SettingsConfigDict


class BusinessImpactServiceSettings(BaseSettings):
    """
    Business Impact Service's own configuration (Part 6) -- destination
    URLs for delivering the BusinessImpactCompleted event to its two
    independent consumers (Batch 4B SS2/SS5's parallel fan-out:
    recommendation_service and evaluation_service, never chained).

    Reuses the exact RECOMMENDATION_SERVICE_URL/EVALUATION_SERVICE_URL env
    vars gateway_service already reads (see .env/.env.example) -- every
    service's container already receives them via docker-compose's shared
    `env_file: .env` directive, so no new environment variables were
    required; only this service's own settings object was missing.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    RECOMMENDATION_SERVICE_URL: str = "http://localhost:8006"
    EVALUATION_SERVICE_URL: str = "http://localhost:8008"

    # Deliberately short and local to this one outbound call, not shared
    # with the Engine's own request/response cycle -- a slow/unreachable
    # consumer must never make POST /business-impact itself hang.
    EVENT_DELIVERY_TIMEOUT_SECONDS: float = 5.0


settings = BusinessImpactServiceSettings()
