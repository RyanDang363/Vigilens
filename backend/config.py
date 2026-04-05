from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Workspace Safety Monitor"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    twelvelabs_api_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    secret_key: str = "change-me-in-production"
    fetchai_seed_phrase: str = ""

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
