"""Compile the research StateGraph once (PAT-01, PAT-07)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from plan_based_researcher.agents.factory import AgentFactory
from plan_based_researcher.eval.strategies import ResearchEvalStrategy, WriterEvalStrategy
from plan_based_researcher.graph.nodes.evaluate import make_evaluate_node
from plan_based_researcher.graph.nodes.execute import make_execute_node
from plan_based_researcher.graph.nodes.finalize import make_finalize_node
from plan_based_researcher.graph.nodes.gate import make_gate_node
from plan_based_researcher.graph.nodes.planner import make_planner_node
from plan_based_researcher.graph.state import GraphState

__all__ = ["GraphDeps", "build_graph"]


@dataclass(frozen=True, slots=True)
class GraphDeps:
    factory: AgentFactory
    research_eval: ResearchEvalStrategy
    writer_eval: WriterEvalStrategy


def _after_gate(state: GraphState) -> Literal["planner", "finalize"]:
    if state.get("outcome") == "refused":
        return "finalize"
    return "planner"


def _after_evaluate(state: GraphState) -> Literal["execute", "finalize"]:
    outcome = state.get("outcome") or "pending"
    if outcome in ("done", "insufficient", "error", "refused"):
        return "finalize"
    return "execute"


def build_graph(deps: GraphDeps, checkpointer: Any | None = None):
    """Compile gate → planner → execute ↔ evaluate → finalize."""
    graph = StateGraph(GraphState)
    graph.add_node("gate", make_gate_node(deps.factory))
    graph.add_node("planner", make_planner_node(deps.factory))
    graph.add_node("execute", make_execute_node(deps.factory))
    graph.add_node(
        "evaluate",
        make_evaluate_node(deps.research_eval, deps.writer_eval),
    )
    graph.add_node("finalize", make_finalize_node())

    graph.add_edge(START, "gate")
    graph.add_conditional_edges(
        "gate",
        _after_gate,
        {"planner": "planner", "finalize": "finalize"},
    )
    graph.add_edge("planner", "execute")
    graph.add_edge("execute", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        _after_evaluate,
        {"execute": "execute", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)
