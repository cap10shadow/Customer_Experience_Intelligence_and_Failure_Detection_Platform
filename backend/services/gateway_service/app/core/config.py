from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """
    Gateway-local configuration, deliberately separate from
    backend.shared.config.settings.Settings: downstream service URLs and
    Gateway-specific timeout/CORS values are a Gateway concern, not
    something every other backend service should carry in its own
    settings object.

    Defaults target local (non-Docker) development, matching the
    localhost-default convention already used by the shared Settings'
    POSTGRES_HOST. The .env file overrides these to Docker service-name
    URLs (e.g. http://anomaly_service:8003) for the docker-compose
    runtime, the same way it already overrides POSTGRES_HOST to
    "postgres" there.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"

    INGESTION_SERVICE_URL: str = "http://localhost:8001"
    NLP_SERVICE_URL: str = "http://localhost:8002"
    ANOMALY_SERVICE_URL: str = "http://localhost:8003"
    ROOT_CAUSE_SERVICE_URL: str = "http://localhost:8004"
    BUSINESS_IMPACT_SERVICE_URL: str = "http://localhost:8005"
    RECOMMENDATION_SERVICE_URL: str = "http://localhost:8006"
    COPILOT_SERVICE_URL: str = "http://localhost:8007"
    EVALUATION_SERVICE_URL: str = "http://localhost:8008"

    DOWNSTREAM_TIMEOUT_SECONDS: float = 5.0

    # Comma-separated list, kept as a plain string rather than a typed
    # list so a .env edit doesn't need JSON-array syntax.
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Phase 13 Batch 2 (AD-1/AD-6): the Gateway's own JWT session signing
    # key. The default below is an explicit, obviously-fake development
    # secret -- the same weak-dev-default convention already used by
    # POSTGRES_PASSWORD ("postgres") and GF_SECURITY_ADMIN_PASSWORD
    # ("admin") elsewhere in this repository, always overridable via
    # .env, and flagged (§19 of the frozen architecture) as requiring
    # rotation before any real deployment. Never a VITE_* variable --
    # this must never reach frontend/browser code.
    JWT_SECRET_KEY: str = "dev-only-insecure-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    # Short-lived per AD-6 ("short-lived JWT"); no refresh token exists
    # in this batch, so this is also the platform's full session length
    # today -- a user must log in again after this many minutes.
    JWT_EXPIRE_MINUTES: int = 30

    @property
    def downstream_service_urls(self) -> dict[str, str]:
        return {
            "ingestion": self.INGESTION_SERVICE_URL,
            "nlp": self.NLP_SERVICE_URL,
            "anomaly": self.ANOMALY_SERVICE_URL,
            "root_cause": self.ROOT_CAUSE_SERVICE_URL,
            "business_impact": self.BUSINESS_IMPACT_SERVICE_URL,
            "recommendation": self.RECOMMENDATION_SERVICE_URL,
            "copilot": self.COPILOT_SERVICE_URL,
            "evaluation": self.EVALUATION_SERVICE_URL,
        }

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = GatewaySettings()
