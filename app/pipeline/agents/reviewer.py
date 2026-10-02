from app.core import llm
from app.core.llm import LLMError


def reviewer_agent(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    report = state["report"]
    topic = state["topic"]

    prompt = f"""You are a quality review agent. Review the report
and improve it.

Topic: {topic}
Report: {report}

Review for:
1. Accuracy and factual correctness
2. Clarity and readability
3. Completeness
4. Professional tone
5. Actionable recommendations

Provide the final improved version of the report."""

    try:
        content = llm.invoke_llm(prompt, temperature=0.1, stage="reviewer")
    except LLMError as exc:
        return {**state, "status": "failed", "error": f"Reviewer stage failed: {exc}"}

    return {
        **state,
        "final_report": content,
        "status": "done",
    }
