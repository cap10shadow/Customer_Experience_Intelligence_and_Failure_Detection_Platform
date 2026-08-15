from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Phase 11 Batch 2 -- distributed tracing. Default endpoint matches
    # docker-compose.yml's `otel-collector` service name/OTLP gRPC port;
    # overridden to localhost for non-Docker local development the same
    # way POSTGRES_HOST already is. TRACING_ENABLED lets a test process
    # (or a local run with no collector available) opt out entirely
    # rather than fail/retry against an unreachable endpoint.
    TRACING_ENABLED: bool = True
    OTLP_EXPORTER_ENDPOINT: str = "otel-collector:4317"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "operational_intelligence"
    # Default to localhost for local development; Docker overrides this via .env (POSTGRES_HOST=postgres)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    # Phase 13 Batch 4 (AD-5): the shared internal service-to-service
    # credential (backend/shared/security/internal_auth.py). Lives here,
    # not any one service's local settings, since every service that
    # sends or validates it needs the identical value. Same weak-dev-
    # default convention as POSTGRES_PASSWORD/JWT_SECRET_KEY -- always
    # overridable via .env, flagged as requiring rotation before any
    # real deployment (§19 of the frozen architecture). Never a VITE_*
    # variable; never reaches frontend/browser code.
    INTERNAL_SERVICE_SECRET: str = "dev-only-insecure-internal-secret-change-in-production"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
