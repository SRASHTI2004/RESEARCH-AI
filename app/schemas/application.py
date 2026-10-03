from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ApplicationStatus = Literal["saved", "applied", "referral_asked", "interview", "rejected", "offer"]


class ApplicationCreate(BaseModel):
    """Either `job_id` (track a job from the feed) or title+company (a role
    found elsewhere)."""

    job_id: str | None = None
    title: str | None = Field(None, max_length=300)
    company: str | None = Field(None, max_length=200)
    url: str = Field("", max_length=1000)
    location: str = Field("", max_length=500)
    status: ApplicationStatus = "saved"
    notes: str = Field("", max_length=10_000)
    follow_up_on: date | None = None

    @model_validator(mode="after")
    def job_or_manual(self) -> "ApplicationCreate":
        if not self.job_id and not (
            self.title and self.title.strip() and self.company and self.company.strip()
        ):
            raise ValueError("give either job_id, or both title and company")
        return self


class ApplicationUpdate(BaseModel):
    """Only fields actually sent are changed; send `"follow_up_on": null`
    to clear the reminder."""

    status: ApplicationStatus | None = None
    notes: str | None = Field(None, max_length=10_000)
    follow_up_on: date | None = None
    applied_on: date | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str | None
    title: str
    company: str
    url: str
    location: str
    status: ApplicationStatus
    notes: str
    applied_on: date | None
    follow_up_on: date | None
    created_at: datetime
    updated_at: datetime
    job_score: int | None = None


class ApplicationList(BaseModel):
    items: list[ApplicationOut]
    counts: dict[str, int]
