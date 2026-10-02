from fastapi import FastAPI
from pydantic import BaseModel
from app.graph import run_research

app = FastAPI(
    title="ResearchAI — Multi Agent System",
    description="4 AI agents collaborate to research any topic",
    version="1.0.0"
)


class ResearchRequest(BaseModel):
    topic: str


@app.get("/")
def root():
    return {"message": "ResearchAI is running!"}


@app.post("/research")
def research(request: ResearchRequest):
    if not request.topic.strip():
        return {"error": "Topic cannot be empty"}

    result = run_research(request.topic)

    return {
        "topic": request.topic,
        "research": result["research"],
        "analysis": result["analysis"],
        "report": result["report"],
        "final_report": result["final_report"],
        "status": result["status"]
    }
