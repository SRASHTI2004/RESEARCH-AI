from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)

    @field_validator("company")
    @classmethod
    def company_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("company cannot be blank")
        return value


class Source(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    title: str
    url: str
    snippet: str


class ResearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company: str
    research: str
    analysis: str
    report: str
    final_report: str
    sources: list[Source]
    status: str
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ResearchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company: str
    status: str
    created_at: datetime
