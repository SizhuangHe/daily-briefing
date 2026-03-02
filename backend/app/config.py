from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Gemini API
    gemini_api_key: str = ""
    gemini_primary_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-2.0-flash-lite"

    # Database
    database_url: str = "sqlite:///data/daily_briefing.db"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Calendar provider: "google" or "apple"
    calendar_provider: str = "google"

    # CORS
    frontend_url: str = "http://localhost:5173"

    model_config = {
        "env_file": ("../.env", ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
