from fastapi import FastAPI
from pydantic import BaseModel
from app.graph import run_research

app = FastAPI(
    title="ResearchAI — Multi Agent System",
    description="4 AI agents with real web search and feedback loop",
    version="2.0.0"
)


class ResearchRequest(BaseModel):
    topic: str


@app.get("/")
def root():
    return {
        "message": "ResearchAI v2.0 is running!",
        "agents": ["Researcher (web search)", "Analyzer", "Writer", "Reviewer (feedback loop)"]
    }


@app.post("/research")
def research(request: ResearchRequest):
    if not request.topic.strip():
        return {"error": "Topic cannot be empty"}

    result = run_research(request.topic)

    return {
        "topic": request.topic,
        "research": result.get("research", ""),
        "sources": result.get("sources", ""),
        "analysis": result.get("analysis", ""),
        "report": result.get("report", ""),
        "final_report": result.get("final_report", ""),
        "quality_score": result.get("quality_score", 0),
        "improvements": result.get("improvements", ""),
        "review_count": result.get("review_count", 1),
        "status": result.get("status", "done")
    }