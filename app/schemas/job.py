from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    company: str
    location: str
    is_remote: bool
    url: str
    source: str
    official_source: bool
    salary_text: str
    posted_at: datetime | None
    first_seen_at: datetime
    passed_prefilter: bool
    prefilter_reason: str
    rule_score: int
    red_flags: list[str]
    llm_score: int | None
    llm_reason: str | None
    fresher_friendly: bool | None
    # llm_score when present, else rule_score — what lists are sorted by.
    score: int


class JobDetail(JobSummary):
    description: str
    employment_type: str
    tags: list[str]
    salary_min: float | None
    salary_max: float | None
    salary_currency: str
    last_seen_at: datetime


class JobList(BaseModel):
    items: list[JobSummary]
    total: int


class SourceRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    fetched_count: int
    new_count: int
    message: str


class SearchStringOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    query: str
    where: str
    url: str


class MessageDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    title: str
    body: str
    char_count: int


class ReferralKitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    search_strings: list[SearchStringOut]
    checklist: list[str]
    drafts: list[MessageDraftOut]
    notes: list[str]
