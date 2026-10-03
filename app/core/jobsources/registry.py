import logging

from app.core.config import settings
from app.core.jobsources.aggregators import (
    AdzunaSource,
    ArbeitnowSource,
    HimalayasSource,
    RemoteOKSource,
    RemotiveSource,
    WeWorkRemotelySource,
)
from app.core.jobsources.ats import AshbySource, GreenhouseSource, LeverSource, load_companies
from app.core.jobsources.base import JobSource
from app.core.profile import Profile

logger = logging.getLogger(__name__)

ALL_SOURCE_NAMES = (
    "greenhouse",
    "lever",
    "ashby",
    "remotive",
    "remoteok",
    "weworkremotely",
    "himalayas",
    "arbeitnow",
    "adzuna",
)


def build_sources(profile: Profile, names: list[str] | None = None) -> list[JobSource]:
    """Instantiate the enabled sources (JOB_SOURCES, or `names` to override)."""
    wanted = names or [n.strip() for n in settings.job_sources.split(",") if n.strip()]
    companies = load_companies()
    queries = profile.search_queries

    factories = {
        "greenhouse": lambda: GreenhouseSource(companies),
        "lever": lambda: LeverSource(companies),
        "ashby": lambda: AshbySource(companies),
        "remotive": RemotiveSource,
        "remoteok": RemoteOKSource,
        "weworkremotely": WeWorkRemotelySource,
        "himalayas": lambda: HimalayasSource(queries),
        "arbeitnow": ArbeitnowSource,
        "adzuna": lambda: AdzunaSource(queries),
    }

    sources: list[JobSource] = []
    for name in wanted:
        factory = factories.get(name)
        if factory is None:
            logger.warning("Unknown job source '%s' in JOB_SOURCES, skipping", name)
            continue
        sources.append(factory())
    return sources
