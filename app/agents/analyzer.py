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

    print(f"  [Analyzer] Analyzing research on: {topic}")

    prompt = f"""You are a senior analyst. Deeply analyze the research provided.

Topic: {topic}

Research Data:
{research}

Provide a structured analysis with:

1. **Top 5 Key Insights** — The most important takeaways, ranked by significance.

2. **Patterns & Trends** — What patterns are emerging? What is accelerating or declining?

3. **Critical Findings** — What is surprising, counterintuitive, or especially important?

4. **SWOT-Style Assessment**:
   - Strengths / Opportunities
   - Weaknesses / Risks / Threats

5. **Research Gaps** — What questions remain unanswered? What data is missing?

6. **Confidence Level** — How reliable is this data? Rate 1-10 and explain why.

Be analytical, critical, and precise. Do not just restate the research — synthesize it."""

    response = llm.invoke(prompt)

    return {
        **state,
        "analysis": response.content,
        "status": "analysis_done"
    }