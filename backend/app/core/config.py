from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in project root (parent of backend/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "DEBUG"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://sahidawa:changeme@localhost:5432/sahidawa"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Meilisearch
    meili_url: str = "http://localhost:7700"
    meili_master_key: str = "changeme_meili_master_key"

    # Groq LLM
    groq_api_key: str = ""
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 512

    # WhatsApp
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_api_version: str = "v21.0"

    # Google Maps
    google_maps_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_secret_key: str = ""

    @property
    def whatsapp_api_url(self) -> str:
        return (
            f"https://graph.facebook.com/{self.whatsapp_api_version}"
            f"/{self.whatsapp_phone_number_id}/messages"
        )


settings = Settings()
