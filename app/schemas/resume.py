from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.resume import Resume


class MasterResumeStatus(BaseModel):
    exists: bool
    message: str
    name: str = ""
    experience: int = 0
    projects: int = 0
    skills: int = 0


class DiffLineOut(BaseModel):
    op: str
    text: str


class TailoredResumeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str | None
    job_title: str
    company: str
    used_llm: bool
    created_at: datetime


class TailoredResumeOut(TailoredResumeSummary):
    content: Resume
    diff: list[DiffLineOut]
    warnings: list[str]
    keywords_matched: list[str]
    keywords_missing: list[str]
