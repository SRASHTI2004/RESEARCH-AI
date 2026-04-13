from langgraph.graph import StateGraph, END
from typing import TypedDict
from app.agents.researcher import researcher_agent
from app.agents.analyzer import analyzer_agent
from app.agents.writer import writer_agent
from app.agents.reviewer import reviewer_agent, should_rewrite


class AgentState(TypedDict):
    topic: str
    research: str
    sources: str
    analysis: str
    report: str
    final_report: str
    quality_score: int
    improvements: str
    review_count: int
    status: str


def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("analyzer", analyzer_agent)
    workflow.add_node("writer", writer_agent)
    workflow.add_node("reviewer", reviewer_agent)

    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "analyzer")
    workflow.add_edge("analyzer", "writer")
    workflow.add_edge("writer", "reviewer")

    workflow.add_conditional_edges(
        "reviewer",
        should_rewrite,
        {
            "rewrite": "writer",
            "done": END
        }
    )

    return workflow.compile()


def run_research(topic: str) -> dict:
    graph = create_graph()

    initial_state = {
        "topic": topic,
        "research": "",
        "sources": "",
        "analysis": "",
        "report": "",
        "final_report": "",
        "quality_score": 0,
        "improvements": "",
        "review_count": 0,
        "status": "starting"
    }

    print(f"\n{'='*50}")
    print(f"Starting Research: {topic}")
    print(f"{'='*50}")

    result = graph.invoke(initial_state)

    print(f"\nDone! Quality Score: {result.get('quality_score', 'N/A')}/10")

    return result