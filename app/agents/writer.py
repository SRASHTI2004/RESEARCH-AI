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

    print(f"  [Writer] Writing report on: {topic}")

    prompt = f"""You are a professional report writer. Write a comprehensive, publication-ready report.

Topic: {topic}

Research:
{research}

Analysis:
{analysis}

Write a professional report with this exact structure:

---
# {topic}: A Comprehensive Research Report

## Executive Summary
(3-4 sentences: the most critical findings and why they matter)

## 1. Introduction
(Context, why this topic matters, scope of this report)

## 2. Current Landscape
(What's happening now — use specific facts, numbers, examples from the research)

## 3. Key Findings
(The 5 most important things we found, with evidence)

## 4. Deep Analysis
(Patterns, causes, implications — this is where insight lives)

## 5. Risks & Challenges
(What could go wrong? What obstacles exist?)

## 6. Future Outlook
(Where is this heading? Short-term vs long-term)

## 7. Conclusions & Recommendations
(What should the reader DO with this information? Actionable steps)

## Sources & References
(List sources from the research if available)
---

Write in clear, professional English. Use specific data points. Avoid vague statements.
Make it engaging — this should be a report someone actually wants to read."""

    response = llm.invoke(prompt)

    return {
        **state,
        "report": response.content,
        "status": "writing_done"
    }