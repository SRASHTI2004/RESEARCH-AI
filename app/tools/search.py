from tavily import TavilyClient
from app.config import TAVILY_API_KEY


def web_search(query: str, max_results: int = 5) -> str:
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
        )

        results = []

        if response.get("answer"):
            results.append(f"SUMMARY: {response['answer']}\n")

        for i, result in enumerate(response.get("results", []), 1):
            results.append(
                f"[Source {i}] {result.get('title', 'No Title')}\n"
                f"URL: {result.get('url', '')}\n"
                f"Content: {result.get('content', '')}\n"
            )

        return "\n".join(results) if results else "No results found."

    except Exception as e:
        return f"Search failed: {str(e)}. Proceeding with LLM knowledge."