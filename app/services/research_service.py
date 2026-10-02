from app.pipeline.graph import run_research as _run_research


def run_research(topic: str) -> dict:
    """Thin orchestration layer over the pipeline.

    Kept separate from the router/pipeline so persistence and search
    integration (added in later phases) have one place to live without
    routers reaching into pipeline internals directly.
    """
    return _run_research(topic)
