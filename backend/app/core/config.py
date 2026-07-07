from functools import lru_cache

from pydantic import field_validator
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

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

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
