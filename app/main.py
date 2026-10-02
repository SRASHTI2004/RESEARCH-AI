import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, health, research
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

if settings.secret_key == "dev-secret-change-me-in-production":
    logger.warning(
        "SECRET_KEY is using the insecure default — set a real value in .env "
        "before deploying (see .env.example)."
    )

app = FastAPI(
    title="ResearchAI — Company Research Brief",
    description="Multi-agent pipeline that researches a company via live web search "
    "and produces a sourced, cited brief: overview, recent news, tech stack, "
    "and interview prep questions.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(research.router)
