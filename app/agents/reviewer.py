from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, MODEL


def reviewer_agent(state: dict) -> dict:
    llm = ChatGroq(
        model=MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.1
    )

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

    response = llm.invoke(prompt)

    return {
        **state,
        "final_report": response.content,
        "status": "review_done"
    }