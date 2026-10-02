from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict:
    return {"message": "ResearchAI is running!"}


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
