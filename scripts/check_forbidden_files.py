"""Fail if any secret or personal file is tracked/staged in git.

.gitignore stops accidental `git add .`, but not `git add -f` or a file
that was tracked before an ignore rule existed — this check catches both.
Runs in pre-commit (on staged files) and CI (on every tracked file).

    python scripts/check_forbidden_files.py            # all tracked files
    python scripts/check_forbidden_files.py a.txt b.py # just these paths
"""

import fnmatch
import subprocess
import sys

# (glob pattern, why it's forbidden)
FORBIDDEN = [
    (".env", "secrets (API keys, SMTP password, Telegram token)"),
    (".env.*", "secrets"),
    ("*/.env", "secrets"),
    ("*/.env.*", "secrets"),
    ("config/profile.yaml", "personal profile data"),
    ("data/private/*", "private data (master resume etc.)"),
    ("*.db", "local database (contains your tracker, notes and tailored resumes)"),
    ("*.sqlite3", "local database"),
    ("*resume*.pdf", "resume file"),
    ("*resume*.docx", "resume file"),
    ("*Resume*.pdf", "resume file"),
    ("*Resume*.docx", "resume file"),
    ("docs/INTERVIEW_NOTES.md", "personal study notes"),
    ("docs/PROGRESS.md", "personal progress log"),
    ("docs/PROJECT_GUIDE.*", "personal learning guide"),
    ("docs/notes/*", "personal study notes"),
    ("*.pem", "private key"),
    ("*.key", "private key"),
]

ALLOWED = {".env.example", "frontend/.env.example"}


def violations(paths: list[str]) -> list[tuple[str, str]]:
    found = []
    for raw in paths:
        path = raw.replace("\\", "/")
        if path in ALLOWED or path.endswith(".example") or ".example." in path:
            continue
        for pattern, why in FORBIDDEN:
            if fnmatch.fnmatch(path, pattern):
                found.append((path, why))
                break
    return found


def main(argv: list[str]) -> int:
    paths = (
        argv
        or subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    )
    bad = violations(paths)
    for path, why in bad:
        print(f"FORBIDDEN: {path} - {why}. Unstage it: git rm --cached {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
