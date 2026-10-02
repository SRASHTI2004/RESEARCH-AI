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

    # Comma-separated. Dev default is the Vite dev server origin; tighten
    # for prod via env.
    cors_origins: str = "http://localhost:5173"

    # --- Rate limiting ---
    # "memory://" is fine for a single dev process; a multi-worker prod
    # deployment should point this at the same Redis instance Celery uses
    # (e.g. "redis://redis:6379/1" — a different DB index, so rate-limit
    # keys never collide with Celery's).
    rate_limit_storage_uri: str = "memory://"

    # --- Object storage (optional) ---
    # Unset by default — gracefully skipped (no export upload, no error)
    # when any of these are blank, same pattern as an unconfigured LLM
    # provider. MinIO locally (docker-compose), any S3-compatible service
    # (including real AWS S3) in production by just changing these.
    storage_endpoint_url: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_bucket_name: str = "researchai-reports"

    database_url: str = "sqlite:///./app.db"

    # --- Auth ---
    # Generate a real one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    secret_key: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Async job processing ---
    # Eager mode (the default: no Redis needed) runs tasks
    # synchronously in-process via .delay() — no broker needed. Set False
    # (docker-compose does) for a real background worker process.
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
