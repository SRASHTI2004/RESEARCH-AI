from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
    index: int
    title: str
    url: str
    snippet: str


class ResearchResponse(BaseModel):
    company: str
    research: str
    analysis: str
    report: str
    final_report: str
    sources: list[Source]
    status: str
    error: Optional[str] = None
