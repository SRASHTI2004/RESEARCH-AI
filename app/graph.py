from langgraph.graph import StateGraph, END
from typing import TypedDict
from app.agents.researcher import researcher_agent
from app.agents.analyzer import analyzer_agent
from app.agents.writer import writer_agent
from app.agents.reviewer import reviewer_agent


class AgentState(TypedDict):
    topic: str
    research: str
    analysis: str
    report: str
    final_report: str
    status: str


def create_graph():
    workflow = StateGraph(AgentState)

    # Add all agents as nodes
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("analyzer", analyzer_agent)
    workflow.add_node("writer", writer_agent)
    workflow.add_node("reviewer", reviewer_agent)

    # Define flow
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "analyzer")
    workflow.add_edge("analyzer", "writer")
    workflow.add_edge("writer", "reviewer")
    workflow.add_edge("reviewer", END)

    return workflow.compile()


def run_research(topic: str) -> dict:
    graph = create_graph()

    initial_state = {
        "topic": topic,
        "research": "",
        "analysis": "",
        "report": "",
        "final_report": "",
        "status": "starting"
    }

    print(f"\nStarting research on: {topic}")
    print("Agent 1 — Researcher working...")

    result = graph.invoke(initial_state)

    print("Agent 2 — Analyzer working...")
    print("Agent 3 — Writer working...")
    print("Agent 4 — Reviewer working...")
    print("\nDone!")

    return result