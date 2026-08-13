from pydantic_settings import BaseSettings, SettingsConfigDict


class CopilotServiceSettings(BaseSettings):
    """
    Copilot Service's own configuration (Phase 12 Batch 2) -- the
    authoritative domain services its read-only tool adapters call
    directly (docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md §8/§9,
    Tool Contract Matrix §13). Reuses the exact env vars gateway_service
    already reads (see .env/.env.example) -- every service's container
    already receives them via docker-compose's shared `env_file: .env`
    directive, so no new environment variable was required.

    Deliberately excludes ingestion_service and copilot_service's own
    URL (no tool calls either) and gateway_service's URL (tools must
    never call the public Gateway -- see the architecture's Investigation/
    Analytics/Administration tool designs).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ANOMALY_SERVICE_URL: str = "http://localhost:8003"
    ROOT_CAUSE_SERVICE_URL: str = "http://localhost:8004"
    BUSINESS_IMPACT_SERVICE_URL: str = "http://localhost:8005"
    RECOMMENDATION_SERVICE_URL: str = "http://localhost:8006"
    NLP_SERVICE_URL: str = "http://localhost:8002"

    # Administration/Configuration Read Tool (§13.7): the same simple
    # per-service /health loop administration_aggregator.py already
    # performs, reimplemented here directly (never via the Gateway) --
    # deliberately excludes gateway_service (never called) and
    # copilot_service itself (if this code is executing, the process is
    # up, exactly like the Gateway's own self-health rationale).
    INGESTION_SERVICE_URL: str = "http://localhost:8001"
    EVALUATION_SERVICE_URL: str = "http://localhost:8008"

    @property
    def health_check_targets(self) -> dict[str, str]:
        return {
            "ingestion": self.INGESTION_SERVICE_URL,
            "nlp": self.NLP_SERVICE_URL,
            "anomaly": self.ANOMALY_SERVICE_URL,
            "root_cause": self.ROOT_CAUSE_SERVICE_URL,
            "business_impact": self.BUSINESS_IMPACT_SERVICE_URL,
            "recommendation": self.RECOMMENDATION_SERVICE_URL,
            "evaluation": self.EVALUATION_SERVICE_URL,
        }


settings = CopilotServiceSettings()
