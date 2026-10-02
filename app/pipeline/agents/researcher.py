from app.core import llm
from app.core.llm import LLMError


def researcher_agent(state: dict) -> dict:
    topic = state["topic"]

    prompt = f"""You are a research agent. Your job is to gather
comprehensive information about the given topic.

Topic: {topic}

Provide detailed research covering:
1. Overview and background
2. Current state and trends
3. Key facts and statistics
4. Important developments
5. Future outlook

Be thorough and factual."""

    try:
        content = llm.invoke_llm(prompt, temperature=0.3, stage="researcher")
    except LLMError as exc:
        return {**state, "status": "failed", "error": f"Researcher stage failed: {exc}"}

    return {
        **state,
        "research": content,
        "status": "researching",
    }
