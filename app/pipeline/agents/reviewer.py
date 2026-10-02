from app.core import llm
from app.core.llm import LLMError
from app.pipeline.sourcing import format_source_list


def reviewer_agent(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    company = state["company"]
    report = state["report"]
    sources = state["sources"]

    prompt = f"""You are a quality review agent fact-checking a sourced
Company Research Brief before it's shown to a job candidate.

Company: {company}
Available sources (the ONLY valid citation numbers): {format_source_list(sources)}

Draft report:
{report}

Review instructions:
1. Check every factual claim has a [n] citation whose number exists in the
   source list above.
2. Improve clarity, structure, and professional tone. Keep all valid
   citations intact and the Sources section accurate.
3. Do not invent new facts or citations.

Output the final, polished report, then append a final section titled
"Verification Notes" listing:
- Any claim you found with NO citation, or with a citation number not in
  the source list (quote the claim briefly).
- Write "No issues found." if there are none.

This Verification Notes section is for transparency — it must always be
present, even when everything checks out."""

    try:
        content = llm.invoke_llm(prompt, temperature=0.1, stage="reviewer")
    except LLMError as exc:
        return {**state, "status": "failed", "error": f"Reviewer stage failed: {exc}"}

    return {
        **state,
        "final_report": content,
        "status": "done",
    }
