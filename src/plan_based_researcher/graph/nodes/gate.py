"""Gate graph node: domain check then custom `gate` event (GATE-01, GATE-02)."""

from __future__ import annotations

from langgraph.config import get_stream_writer

from plan_based_researcher.agents.factory import AgentFactory
from plan_based_researcher.graph.state import GraphState


def make_gate_node(factory: AgentFactory):
    async def gate(state: GraphState) -> dict:
        writer = get_stream_writer()
        update = await factory.create("gate").run(state)
        data = update.get("gate") or {}
        writer({"event": "gate", "data": data})
        return update

    return gate
