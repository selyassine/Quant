from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "QuantAI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change_this_in_production"

    # Database
    postgres_user: str = "quantai"
    postgres_password: str = "quantai_secret"
    postgres_db: str = "quantai"
    database_url: str = "postgresql+asyncpg://quantai:quantai_secret@db:5432/quantai"
    database_url_sync: str = "postgresql://quantai:quantai_secret@db:5432/quantai"

    # Redis & Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Alpaca
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets/v2"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()