from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Ordered fallback chain. Supported names: gemini, groq, ollama
    llm_provider_order: str = "gemini,groq"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_writer_model: str = "gemini-2.0-flash"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_writer_model: str = "llama-3.3-70b-versatile"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 3

    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
