"""The master resume: a structured YAML file in data/private/ (git-ignored).

Structured on purpose — every bullet has a stable ID, so the tailoring
step can only *reorder and reword existing items*; it has no way to add
an experience, project or skill that isn't already here.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.core.config import settings


class Contact(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    links: dict[str, str] = Field(default_factory=dict)


class SkillGroup(BaseModel):
    group: str
    items: list[str]


class Experience(BaseModel):
    id: str
    title: str
    org: str
    location: str = ""
    start: str = ""
    end: str = ""
    tech: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class Project(BaseModel):
    id: str
    name: str
    link: str = ""
    tech: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str
    school: str
    location: str = ""
    start: str = ""
    end: str = ""
    score: str = ""


class Resume(BaseModel):
    contact: Contact
    summary: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)

    def all_text(self) -> str:
        """Every word in the resume — the universe a tailored version may draw from."""
        parts = [self.summary]
        parts += [i for g in self.skills for i in g.items]
        for e in self.experience:
            parts += [e.title, e.org, *e.tech, *e.bullets]
        for p in self.projects:
            parts += [p.name, *p.tech, *p.bullets]
        for ed in self.education:
            parts += [ed.degree, ed.school, ed.score]
        parts += self.achievements
        return "\n".join(parts)


class MasterResumeMissingError(Exception):
    pass


def load_master_resume(path: str | None = None) -> Resume:
    resume_path = Path(path or settings.master_resume_path)
    if not resume_path.exists():
        raise MasterResumeMissingError(
            f"No master resume at {resume_path}. Copy data/master_resume.example.yaml to "
            f"{settings.master_resume_path} and fill in your real experience."
        )
    data = yaml.safe_load(resume_path.read_text(encoding="utf-8")) or {}
    return Resume.model_validate(data)
