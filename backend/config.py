from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Workspace Safety Monitor"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    twelvelabs_api_key: str = ""
    secret_key: str = "change-me-in-production"
    fetchai_seed_phrase: str = ""
    training_storage_dir: str = "./backend/storage/training"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
