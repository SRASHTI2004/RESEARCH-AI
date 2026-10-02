from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, MODEL


def researcher_agent(state: dict) -> dict:
    llm = ChatGroq(
        model=MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.3
    )

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

    response = llm.invoke(prompt)

    return {
        **state,
        "research": response.content,
        "status": "research_done"
    }