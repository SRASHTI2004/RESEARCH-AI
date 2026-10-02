from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, MODEL


def analyzer_agent(state: dict) -> dict:
    llm = ChatGroq(
        model=MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.2
    )

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

    response = llm.invoke(prompt)

    return {
        **state,
        "analysis": response.content,
        "status": "analysis_done"
    }