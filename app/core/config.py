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
    groq_model: str = "openai/gpt-oss-20b"
    groq_writer_model: str = "openai/gpt-oss-120b"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 3

    # --- Web search (Researcher stage sourcing) ---
    # Kept small so the synthesis prompt fits inside Groq's free-tier TPM
    # limit (8000 tokens/min) even with no Gemini key configured. Raise
    # these if you have a paid tier or Gemini configured as primary.
    search_provider: str = "duckduckgo"
    search_results_per_query: int = 2
    search_fetch_timeout_seconds: float = 10.0
    search_max_content_chars: int = 1200

    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
