from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, MODEL


def writer_agent(state: dict) -> dict:
    llm = ChatGroq(
        model=MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.4
    )

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

    response = llm.invoke(prompt)

    return {
        **state,
        "report": response.content,
        "status": "writing_done"
    }