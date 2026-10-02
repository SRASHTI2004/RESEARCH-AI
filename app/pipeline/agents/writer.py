from app.core import llm
from app.core.llm import LLMError


def writer_agent(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    topic = state["topic"]
    research = state["research"]
    analysis = state["analysis"]

    prompt = f"""You are a professional writer agent. Write a
comprehensive, well-structured report.

Topic: {topic}
Research: {research}
Analysis: {analysis}

Write a professional report with:
1. Executive Summary
2. Introduction
3. Key Findings
4. Detailed Analysis
5. Conclusions
6. Recommendations

Make it clear, professional and actionable."""

    try:
        content = llm.invoke_llm(prompt, temperature=0.4, stage="writer")
    except LLMError as exc:
        return {**state, "status": "failed", "error": f"Writer stage failed: {exc}"}

    return {
        **state,
        "report": content,
        "status": "writing",
    }
