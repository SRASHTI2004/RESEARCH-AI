from fastapi import FastAPI

from app.api.routers import health, research
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="ResearchAI — Multi Agent System",
    description="4 AI agents collaborate to research any topic",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(research.router)
