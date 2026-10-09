"""Hiring posts from job subreddits, through Reddit's official Data API.

Reddit no longer serves its public JSON to anonymous clients, so this uses
app-only OAuth (client-credentials grant): a free "script" app created at
https://www.reddit.com/prefs/apps gives REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET.
Read-only, no Reddit account login is stored, and it polls each subreddit's
newest posts at most a few times a day (personal, non-commercial use).

Posts are written by individuals, not employers, so every one gets a
"verify the company" flag (job_ingest_service) and is never treated as an
official source.
"""

import logging
import re

from app.core.config import settings
from app.core.jobsources import http
from app.core.jobsources.base import JobSource, NormalizedJob
from app.core.jobsources.text import html_to_text, parse_datetime

logger = logging.getLogger(__name__)

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"

# Subreddits whose posts are about jobs in India; others are treated as remote/global.
INDIA_SUBREDDITS = {"developersindia", "indianstartups", "freshersjobsindia"}

_FOR_HIRE = re.compile(r"\[\s*for\s*hire\s*\]|\bfor hire\b|\bopen to work\b", re.IGNORECASE)
_HIRING_TITLE = re.compile(r"^\s*\[\s*hiring\s*\]|\bwe(?:'re| are) hiring\b|\bhiring\s*[:|\-]", re.IGNORECASE)
_REMOTE = re.compile(r"\bremote\b|\bwork from home\b|\bwfh\b", re.IGNORECASE)


def is_hiring_post(title: str, flair: str | None) -> bool:
    if _FOR_HIRE.search(title) or (flair and _FOR_HIRE.search(flair)):
        return False
    return bool((flair and "hiring" in flair.lower()) or _HIRING_TITLE.search(title))


class RedditSource(JobSource):
    name = "reddit"
    min_interval_hours = 6.0

    def __init__(self, subreddits: list[str] | None = None) -> None:
        configured = [s.strip() for s in settings.reddit_subreddits.split(",") if s.strip()]
        self.subreddits = subreddits or configured

    def is_configured(self) -> bool:
        return bool(settings.reddit_client_id and settings.reddit_client_secret)

    def _token(self) -> str:
        data = http.post_form(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(settings.reddit_client_id, settings.reddit_client_secret),
        )
        return str(data["access_token"])

    def fetch(self) -> list[NormalizedJob]:
        headers = {"Authorization": f"bearer {self._token()}"}
        jobs: list[NormalizedJob] = []
        for sub in self.subreddits:
            listing = http.get_json(
                f"{API}/r/{sub}/new", params={"limit": 100, "raw_json": 1}, headers=headers
            )
            for child in listing.get("data", {}).get("children", []):
                post = child.get("data", {})
                title = post.get("title", "")
                if (
                    post.get("stickied")
                    or post.get("removed_by_category")
                    or not is_hiring_post(title, post.get("link_flair_text"))
                ):
                    continue
                body = html_to_text(post.get("selftext_html")) or post.get("selftext", "")
                text = f"{title}\n{body}"
                in_india = sub.lower() in INDIA_SUBREDDITS
                jobs.append(
                    NormalizedJob(
                        source=self.name,
                        external_id=str(post.get("id", "")),
                        title=title.strip(),
                        company=f"r/{sub} · u/{post.get('author', 'unknown')}",
                        url=f"https://www.reddit.com{post.get('permalink', '')}",
                        location="India" if in_india else "",
                        is_remote=bool(_REMOTE.search(text)) or not in_india,
                        description=body,
                        posted_at=parse_datetime(post.get("created_utc")),
                        tags=[f"r/{sub}"],
                    )
                )
        return jobs
