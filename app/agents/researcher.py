from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, MODEL
from app.tools.search import web_search


def researcher_agent(state: dict) -> dict:
    llm = ChatGroq(
        model=MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.3
    )

    topic = state["topic"]

    print(f"  [Researcher] Searching the web for: {topic}")
    search_results = web_search(topic, max_results=5)

    prompt = f"""You are an expert research agent with access to live web search results.

Topic: {topic}

Live Web Search Results:
{search_results}

Using these real search results AND your knowledge, provide comprehensive research covering:

1. **Overview & Background** — What is this topic? Core concepts.
2. **Current State & Latest Developments** — What is happening RIGHT NOW? Use the search results.
3. **Key Facts & Statistics** — Specific numbers, data, and evidence.
4. **Major Players & Stakeholders** — Who are the key people, companies, or organizations involved?
5. **Future Outlook** — Where is this heading?

Important:
- Cite sources when using information from search results (mention the URL or title).
- Clearly distinguish between established facts and emerging trends.
- Be thorough but precise — quality over quantity.
- If search results contain dates or recent events, include them."""

    response = llm.invoke(prompt)

    return {
        **state,
        "research": response.content,
        "sources": search_results,
        "status": "research_done"
    }