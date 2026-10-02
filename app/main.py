from fastapi import FastAPI

from app.api.routers import health, research
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="ResearchAI — Company Research Brief",
    description="Multi-agent pipeline that researches a company via live web search "
    "and produces a sourced, cited brief: overview, recent news, tech stack, "
    "and interview prep questions.",
    version="2.0.0",
)

app.include_router(health.router)
app.include_router(research.router)
