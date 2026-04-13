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
    review_count = state.get("review_count", 0)

    print(f"  [Reviewer] Reviewing report (attempt {review_count + 1})")

    prompt = f"""You are a senior editor and quality reviewer. Your job is to improve and finalize this report.

Topic: {topic}
Report:
{report}

Review the report strictly for:

1. **Accuracy** — Are all claims backed by evidence? Flag anything unsupported.
2. **Clarity** — Is every paragraph clear and easy to understand?
3. **Completeness** — Are there obvious gaps or missing sections?
4. **Professional Tone** — Is it consistent and authoritative?
5. **Actionability** — Do the recommendations give the reader something concrete to do?

Then provide:
- A quality score out of 10
- A list of specific improvements you made
- The COMPLETE improved final report (not just the changes — the full report)

Format your response as:

QUALITY_SCORE: [X/10]

IMPROVEMENTS_MADE:
- [improvement 1]
- [improvement 2]
...

FINAL_REPORT:
[complete improved report here]"""

    response = llm.invoke(prompt)
    content = response.content

    quality_score = 0
    improvements = ""
    final_report = content

    try:
        if "QUALITY_SCORE:" in content:
            score_line = [l for l in content.split("\n") if "QUALITY_SCORE:" in l][0]
            score_str = score_line.split(":")[1].strip().split("/")[0].strip()
            quality_score = int(score_str)

        if "IMPROVEMENTS_MADE:" in content and "FINAL_REPORT:" in content:
            improvements = content.split("IMPROVEMENTS_MADE:")[1].split("FINAL_REPORT:")[0].strip()
            final_report = content.split("FINAL_REPORT:")[1].strip()
        elif "FINAL_REPORT:" in content:
            final_report = content.split("FINAL_REPORT:")[1].strip()

    except Exception:
        final_report = content

    return {
        **state,
        "final_report": final_report,
        "quality_score": quality_score,
        "improvements": improvements,
        "review_count": review_count + 1,
        "status": "review_done"
    }


def should_rewrite(state: dict) -> str:
    score = state.get("quality_score", 10)
    review_count = state.get("review_count", 0)

    if score < 7 and review_count < 2:
        print(f"  [Reviewer] Score {score}/10 — sending back to writer...")
        return "rewrite"
    else:
        print(f"  [Reviewer] Score {score}/10 — report approved!")
        return "done"