from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.services import usage_service

router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict:
    return {"message": "ResearchAI is running!"}


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/config")
def public_config(db: Session = Depends(get_db)) -> dict:
    """What the frontend needs to know before sign-in: whether to offer
    sign-up and the demo button, and how many AI actions are left today."""
    return {
        "registration_enabled": settings.registration_enabled,
        "demo_enabled": settings.demo_enabled,
        "llm_actions_left_today": usage_service.remaining(db),
    }
