from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.pipeline.agents.analyzer import analyzer_agent
from app.pipeline.agents.researcher import researcher_agent
from app.pipeline.agents.reviewer import reviewer_agent
from app.pipeline.agents.writer import writer_agent


class AgentState(TypedDict):
    company: str
    research: str
    analysis: str
    report: str
    final_report: str
    sources: list[dict]
    status: str
    error: Optional[str]


def _route_on_failure(state: AgentState) -> str:
    return "failed" if state.get("status") == "failed" else "continue"


def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("analyzer", analyzer_agent)
    workflow.add_node("writer", writer_agent)
    workflow.add_node("reviewer", reviewer_agent)

    workflow.set_entry_point("researcher")
    # Each stage short-circuits to END on failure instead of running the
    # remaining (now-meaningless) stages against empty input.
    workflow.add_conditional_edges("researcher", _route_on_failure, {"failed": END, "continue": "analyzer"})
    workflow.add_conditional_edges("analyzer", _route_on_failure, {"failed": END, "continue": "writer"})
    workflow.add_conditional_edges("writer", _route_on_failure, {"failed": END, "continue": "reviewer"})
    workflow.add_edge("reviewer", END)

    return workflow.compile()


def run_research(company: str) -> AgentState:
    graph = create_graph()

    initial_state: AgentState = {
        "company": company,
        "research": "",
        "analysis": "",
        "report": "",
        "final_report": "",
        "sources": [],
        "status": "starting",
        "error": None,
    }

    return graph.invoke(initial_state)
