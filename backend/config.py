from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_THIS_DIR = Path(__file__).resolve().parent
_ENV_CANDIDATES = [_THIS_DIR / ".env", Path.cwd() / ".env"]
_ENV_FILE = next((p for p in _ENV_CANDIDATES if p.is_file()), ".env")


class Settings(BaseSettings):
    app_name: str = "Workspace Safety Monitor"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    twelvelabs_api_key: str = ""
    secret_key: str = "change-me-in-production"
    fetchai_seed_phrase: str = ""
    training_storage_dir: str = "./backend/storage/training"

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
