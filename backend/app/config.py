from pathlib import Path

from pydantic_settings import BaseSettings

# Absolute path to the database
_DB_PATH = Path(__file__).parent.parent / "data" / "daily_briefing.db"


class Settings(BaseSettings):
    # Gemini API
    gemini_api_key: str = ""
    gemini_primary_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-2.5-flash-lite"

    # Database (absolute path)
    database_url: str = f"sqlite:///{_DB_PATH}"

    model_config = {
        "env_file": ("../.env", ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
