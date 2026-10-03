from __future__ import annotations

from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from graph.nodes import (
    node_code,
    node_correct,
    node_critic,
    node_finalize,
    node_gate,
    node_general,
    node_math,
    node_rag,
    node_research,
    node_route,
    node_verify,
)
from graph.router import after_critic, after_gate, after_route
from graph.state import ConversationState, empty_state
from utils.events import EventBus, bus_var


def build_graph():
    graph = StateGraph(ConversationState)
    graph.add_node("route", node_route)
    graph.add_node("general", node_general)
    graph.add_node("research", node_research)
    graph.add_node("rag_node", node_rag)
    graph.add_node("math", node_math)
    graph.add_node("code_agent", node_code)
    graph.add_node("gate", node_gate)
    graph.add_node("verify", node_verify)
    graph.add_node("critic", node_critic)
    graph.add_node("correct", node_correct)
    graph.add_node("finalize", node_finalize)

    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        after_route,
        {
            "general": "general",
            "research": "research",
            "rag": "rag_node",
            "math": "math",
            "code": "code_agent",
        },
    )
    graph.add_edge("general", "gate")
    graph.add_edge("research", "gate")
    graph.add_edge("rag_node", "gate")
    graph.add_edge("math", "gate")
    graph.add_edge("code_agent", "gate")
    graph.add_conditional_edges("gate", after_gate, {"verify": "verify", "finalize": "finalize"})
    graph.add_edge("verify", "critic")
    graph.add_conditional_edges("critic", after_critic, {"correct": "correct", "finalize": "finalize"})
    graph.add_edge("correct", "verify")
    graph.add_edge("finalize", END)
    return graph.compile()


_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP


async def run_workflow(payload: Dict[str, Any], bus: Optional[EventBus] = None) -> ConversationState:
    state: ConversationState = empty_state()
    state.update(payload)  # type: ignore[arg-type]
    if bus is None:
        bus = EventBus()
    token = bus_var.set(bus)
    try:
        app = get_app()
        result = await app.ainvoke(state)
        result["agent_events"] = bus.events
        return result
    finally:
        bus_var.reset(token)
