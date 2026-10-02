from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)

    @field_validator("topic")
    @classmethod
    def topic_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("topic cannot be blank")
        return value


class ResearchResponse(BaseModel):
    topic: str
    research: str
    analysis: str
    report: str
    final_report: str
    status: str
    error: Optional[str] = None
