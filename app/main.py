import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routers import auth, health, jobs, research
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.rate_limit import limiter

configure_logging()
logger = logging.getLogger(__name__)

if settings.secret_key == "dev-secret-change-me-in-production":
    logger.warning(
        "SECRET_KEY is using the insecure default — set a real value in .env "
        "before deploying (see .env.example)."
    )

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if "*" in cors_origins:
    # A wildcard origin combined with allow_credentials=True is both
    # rejected by browsers (per the CORS spec, credentialed requests can
    # never use "*") and a real security footgun if it somehow weren't —
    # fail loudly at startup instead of silently not working.
    raise RuntimeError(
        "CORS_ORIGINS must not contain '*' — list explicit allowed origins. "
        "Credentialed requests (this app sends auth tokens) can't use a wildcard origin."
    )

app = FastAPI(
    title="ResearchAI — Company Research Brief",
    description="Multi-agent pipeline that researches a company via live web search "
    "and produces a sourced, cited brief: overview, recent news, tech stack, "
    "and interview prep questions.",
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
# ^ slowapi's own handler is typed specifically for RateLimitExceeded, which
# is narrower than Starlette's generic Exception handler signature — this
# is how slowapi's own documented usage looks, not a bug in our code.

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(research.router)
app.include_router(jobs.router)
