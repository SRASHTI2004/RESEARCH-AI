from app.core import llm
from app.core.llm import LLMError


def analyzer_agent(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    research = state["research"]
    topic = state["topic"]

    prompt = f"""You are an analysis agent. Analyze the research
provided and extract key insights.

Topic: {topic}
Research: {research}

Provide:
1. Top 5 key insights
2. Main patterns and trends
3. Critical findings
4. Gaps or limitations in the research
5. Recommendations for further exploration

Be analytical and precise."""

    try:
        content = llm.invoke_llm(prompt, temperature=0.2, stage="analyzer")
    except LLMError as exc:
        return {**state, "status": "failed", "error": f"Analyzer stage failed: {exc}"}

    return {
        **state,
        "analysis": content,
        "status": "analyzing",
    }
