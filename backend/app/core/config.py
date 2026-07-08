from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    PROJECT_NAME: str = "Studio OS"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Member invitation links validity.
    INVITE_TOKEN_EXPIRE_DAYS: int = 7

    # Public URL of the frontend, used to build invitation links.
    FRONTEND_URL: str = "http://localhost:5173"

    # Database
    POSTGRES_USER: str = "studio"
    POSTGRES_PASSWORD: str = "studio"
    POSTGRES_DB: str = "studio_os"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Optional full override (used for tests with sqlite)
    DATABASE_URL: str | None = None

    # Redis (background worker + pub/sub for websockets)
    REDIS_URL: str = "redis://localhost:6379/0"
    # Disable Redis-dependent features (worker/pubsub) e.g. in tests.
    REDIS_ENABLED: bool = True

    # Observability
    SENTRY_DSN: str | None = None
    METRICS_ENABLED: bool = True

    # CORS — comma-separated string (avoids pydantic-settings JSON coercion of
    # list fields from env vars). Use the `cors_origins` property to consume.
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
