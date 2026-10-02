from fastapi import APIRouter, HTTPException

from app.schemas.research import ResearchRequest, ResearchResponse
from app.services.research_service import run_research

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchResponse)
def create_research(request: ResearchRequest) -> ResearchResponse:
    result = run_research(request.topic)

    if result.get("status") == "failed":
        raise HTTPException(status_code=502, detail=result.get("error") or "Research pipeline failed")

    return ResearchResponse(**result)
