from app.core import llm
from app.core.llm import LLMError
from app.pipeline.sourcing import format_source_list


def analyzer_agent(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    company = state["company"]
    research = state["research"]
    sources = state["sources"]

    prompt = f"""You are an analysis agent preparing a company research brief.

Company: {company}
Available sources: {format_source_list(sources)}

Sourced research notes:
{research}

Organize this into four clearly-labeled sections, preserving every [n]
citation from the research notes exactly as given (don't invent new ones):
1. Company Overview
2. Recent News
3. Tech Stack
4. Interview Prep Questions (plausible questions a candidate should expect,
   grounded in what the sources actually say about the company)

If a section has little or no source support, say so explicitly rather
than filling it with speculation."""

    try:
        content = llm.invoke_llm(prompt, temperature=0.2, stage="analyzer")
    except LLMError as exc:
        return {**state, "status": "failed", "error": f"Analyzer stage failed: {exc}"}

    return {
        **state,
        "analysis": content,
        "status": "analyzing",
    }
