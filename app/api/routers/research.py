from fastapi import APIRouter, HTTPException

from app.schemas.research import ResearchRequest, ResearchResponse
from app.services.research_service import run_research

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchResponse)
def create_research(request: ResearchRequest) -> ResearchResponse:
    result = run_research(request.company)

    if result.get("status") == "failed":
        raise HTTPException(status_code=502, detail=result.get("error") or "Research pipeline failed")

    # Each source dict carries a "content" field (full fetched text, used for
    # LLM prompts) that the API response doesn't need to expose.
    response_sources = [
        {"index": s["index"], "title": s["title"], "url": s["url"], "snippet": s["snippet"]}
        for s in result.get("sources", [])
    ]

    return ResearchResponse(**{**result, "sources": response_sources})
