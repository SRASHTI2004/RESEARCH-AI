import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_forbidden_files", Path(__file__).resolve().parents[1] / "scripts" / "check_forbidden_files.py"
)
assert _spec and _spec.loader
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.local",
        "frontend/.env",
        "config/profile.yaml",
        "data/private/master_resume.yaml",
        "data/private/notes.txt",
        "app.db",
        "My_Resume.pdf",
        "exports/resume-tailored.docx",
        "data\\private\\master_resume.yaml",
        "docs/INTERVIEW_NOTES.md",
        "docs/PROGRESS.md",
        "docs/PROJECT_GUIDE.html",
        "docs/notes/week1.md",
    ],
)
def test_forbidden_paths_are_caught(path):
    assert check.violations([path])


@pytest.mark.parametrize(
    "path",
    [
        ".env.example",
        "frontend/.env.example",
        "config/profile.example.yaml",
        "data/master_resume.example.yaml",
        "config/companies.yaml",
        "app/services/resume_service.py",
        "docs/DECISIONS.md",
    ],
)
def test_allowed_paths_pass(path):
    assert check.violations([path]) == []


def test_repository_is_currently_clean():
    """The real gate: nothing forbidden is tracked in git right now."""
    assert check.main([]) == 0
