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

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
