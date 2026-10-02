from app.core import llm
from app.core.llm import LLMError
from app.pipeline.sourcing import format_source_list


def writer_agent(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    company = state["company"]
    research = state["research"]
    analysis = state["analysis"]
    sources = state["sources"]

    prompt = f"""You are a professional writer agent producing a polished
Company Research Brief for a job candidate.

Company: {company}
Research notes: {research}
Organized analysis: {analysis}

Write a clear, well-structured brief with these sections, in this order:
1. Executive Summary
2. Company Overview
3. Recent News
4. Tech Stack
5. Interview Prep Questions
6. Sources — a numbered list reproducing every [n] citation used above as
   "[n] Title — URL", using exactly this source list:
{format_source_list(sources)}

Keep every [n] citation inline exactly where it appeared in the research —
never remove a citation, and never introduce a number not in the source
list above."""

    try:
        content = llm.invoke_llm(prompt, temperature=0.4, stage="writer")
    except LLMError as exc:
        return {**state, "status": "failed", "error": f"Writer stage failed: {exc}"}

    return {
        **state,
        "report": content,
        "status": "writing",
    }
