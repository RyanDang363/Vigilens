import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_THIS_DIR = Path(__file__).resolve().parent
_ENV_CANDIDATES = [_THIS_DIR / ".env", Path.cwd() / ".env"]
_ENV_FILE = next((p for p in _ENV_CANDIDATES if p.is_file()), ".env")


class Settings(BaseSettings):
    app_name: str = "Vigilens"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    twelvelabs_api_key: str = ""
    secret_key: str = "change-me-in-production"
    fetchai_seed_phrase: str = ""
    training_storage_dir: str = "./backend/storage/training"

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def describe_twelvelabs_config_for_logs() -> str:
    """Safe one-line summary for debugging auth (never logs the full API key)."""
    s = get_settings()
    key = (s.twelvelabs_api_key or "").strip()
    in_os = "TWELVELABS_API_KEY" in os.environ
    os_raw = os.environ.get("TWELVELABS_API_KEY", "")
    os_nonempty = bool(str(os_raw).strip())
    env_path = str(Path(_ENV_FILE).resolve())
    backend_dotenv = _THIS_DIR / ".env"
    preview = "(empty)"
    if key:
        preview = f"{key[:4]}…{key[-4:]}" if len(key) > 8 else "(short)"
    return (
        f"twelvelabs pydantic env_file={env_path} backend/.env exists={backend_dotenv.is_file()} "
        f"effective_key_len={len(key)} preview={preview} "
        f"TWELVELABS_API_KEY_in_os_environ={in_os} os_value_nonempty={os_nonempty} "
        f"(os env overrides .env when the var is set, even if empty)"
    )
