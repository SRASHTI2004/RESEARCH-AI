from app.core import llm
from app.core.config import settings
from app.core.llm import LLMError
from app.pipeline.sourcing import format_sources_for_prompt, gather_sources


def researcher_agent(state: dict) -> dict:
    company = state["company"]

    try:
        sources = gather_sources(
            company,
            results_per_query=settings.search_results_per_query,
            fetch_timeout=settings.search_fetch_timeout_seconds,
            max_content_chars=settings.search_max_content_chars,
        )
    except Exception as exc:
        return {**state, "status": "failed", "error": f"Search stage failed: {exc}"}

    if not sources:
        return {
            **state,
            "status": "failed",
            "error": f"No web sources could be found or fetched for '{company}'.",
        }

    prompt = f"""You are a research agent gathering sourced information about a company,
for a job candidate preparing to interview there.

Company: {company}

Below are numbered sources found via web search. Use ONLY information from
these sources — do not rely on prior knowledge. Every factual claim you
write MUST include a numbered citation like [1] or [2] matching a source
below. If the sources don't cover something, say so explicitly instead of
guessing.

SOURCES:
{format_sources_for_prompt(sources)}

Write organized research notes covering:
1. Company overview and background
2. Recent news and developments
3. Technology stack and engineering practices (if mentioned anywhere)
4. Anything relevant to interview preparation (culture, values, hiring process)

Cite a source number for every claim."""

    try:
        content = llm.invoke_llm(prompt, temperature=0.3, stage="researcher")
    except LLMError as exc:
        return {**state, "status": "failed", "error": f"Researcher stage failed: {exc}"}

    return {
        **state,
        "research": content,
        "sources": sources,
        "status": "researching",
    }
