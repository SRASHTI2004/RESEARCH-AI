from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Ordered fallback chain. Supported names: gemini, groq, ollama
    llm_provider_order: str = "gemini,groq"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    gemini_writer_model: str = "gemini-flash-latest"
    # Job scoring runs daily in batches — a separate (lite) model keeps it
    # off the brief pipeline's per-model free-tier quota.
    gemini_scoring_model: str = "gemini-flash-lite-latest"

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_writer_model: str = "openai/gpt-oss-120b"
    groq_scoring_model: str = "openai/gpt-oss-20b"

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

    # --- Public deployment ---
    # Self-serve sign-up. Turn off on a public demo so strangers can't spend
    # the free-tier LLM quota; visitors use the demo account instead.
    registration_enabled: bool = True
    # Enables POST /auth/demo (one-click sign-in as a seeded demo user) and
    # `python -m app.cli seed-demo`.
    demo_enabled: bool = False
    demo_email: str = "demo@researchai.local"
    # Site-wide cap on LLM-heavy actions (company briefs + resume tailoring)
    # per rolling 24 h, across all users. 0 = no cap. Gemini's free tier
    # allows ~20 requests/day on the brief model and a brief takes 4.
    llm_daily_action_limit: int = 0

    # --- Async job processing ---
    # Eager mode (the default: no Redis needed) runs tasks
    # synchronously in-process via .delay() — no broker needed. Set False
    # (docker-compose does) for a real background worker process.
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = True

    # --- Job Search Assistant ---
    # Personal files: profile.yaml and the master resume are git-ignored
    # (scripts/check_forbidden_files.py enforces it); the *.example.* files
    # next to them are what's committed.
    profile_path: str = "config/profile.yaml"
    companies_path: str = "config/companies.yaml"
    master_resume_path: str = "data/private/master_resume.yaml"

    # Comma-separated job sources to run. Unknown names are skipped with a
    # warning; sources that need a key (adzuna) skip themselves when unset.
    job_sources: str = (
        "greenhouse,lever,ashby,remotive,remoteok,weworkremotely,himalayas,arbeitnow,adzuna,reddit"
    )
    job_source_timeout_seconds: float = 20.0
    job_source_user_agent: str = "ResearchAI-JobAssistant/1.0 (personal, non-commercial job search)"

    # Adzuna (optional) — free developer key from https://developer.adzuna.com
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "in"
    # Comma-separated places to search (e.g. "Noida,Gurgaon,"); an empty entry
    # searches the whole country (catches remote roles). Default: whole country.
    adzuna_where: str = ""

    # Reddit (optional) — free "script" app at https://www.reddit.com/prefs/apps;
    # read-only app-only OAuth, skipped when unset. Only [Hiring]/"Hiring"-flair posts.
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_subreddits: str = "developersIndia,forhire"

    # LLM scoring: only the top-N rule-ranked jobs per run are sent to the
    # LLM, in batches, with a pause between calls to stay inside free-tier
    # requests-per-minute limits.
    scoring_max_jobs: int = 30
    scoring_batch_size: int = 10
    scoring_min_interval_seconds: float = 13.0

    # --- Daily digest ---
    digest_top_n: int = 10
    # AI-scored jobs below this aren't worth a digest slot.
    digest_min_score: int = 40
    # Only jobs first seen this recently are digest candidates.
    digest_max_age_days: int = 7
    # Used to build "open in app" links inside the digest.
    app_base_url: str = "http://localhost:5173"

    digest_telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    digest_email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    digest_email_from: str = ""
    digest_email_to: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
