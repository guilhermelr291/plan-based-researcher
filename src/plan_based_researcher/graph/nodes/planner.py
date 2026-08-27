"""Planner graph node: emit plan event and store steps on state (PLAN-01)."""

from __future__ import annotations

from langgraph.config import get_stream_writer

from plan_based_researcher.agents.factory import AgentFactory
from plan_based_researcher.graph.state import GraphState


def make_planner_node(factory: AgentFactory):
    async def planner(state: GraphState) -> dict:
        writer = get_stream_writer()
        update = await factory.create("planner").run(state)
        writer({
            "event": "plan",
            "data": {
                "steps": update.get("plan") or [],
                "reuse_existing_papers": update.get("reuse_existing_papers", False),
            },
        })
        update.setdefault("step_index", 0)
        update.setdefault("retry_count", 0)
        update.setdefault("steps_executed", 0)
        return update

    return planner
