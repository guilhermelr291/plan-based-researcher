"""Execute node: dispatch plan[step_index].agent via factory (ORCH-01, PAT-04)."""

from __future__ import annotations

from langgraph.config import get_stream_writer

from plan_based_researcher.agents.factory import AgentFactory
from plan_based_researcher.graph.state import GraphState

__all__ = ["make_execute_node"]


def make_execute_node(factory: AgentFactory):
    async def execute(state: GraphState) -> dict:
        writer = get_stream_writer()
        plan = state.get("plan") or []
        idx = int(state.get("step_index") or 0)
        step = plan[idx] if 0 <= idx < len(plan) else {}
        if not isinstance(step, dict):
            step = {}
        agent = step.get("agent") or ""
        task = step.get("task") or ""
        writer({"event": "step_start", "data": {"agent": agent, "task": task, "step_index": idx}})
        update = await factory.create(agent).run(state)
        papers = update.get("papers") or state.get("papers") or []
        paper_ids = []
        for p in papers:
            if isinstance(p, dict) and p.get("arxiv_id"):
                paper_ids.append(p["arxiv_id"])
        pgvector = update.get("pgvector") or "hit"
        writer({
            "event": "step_end",
            "data": {
                "agent": agent,
                "paper_ids": paper_ids,
                "pgvector": pgvector,
            },
        })
        update["steps_executed"] = (state.get("steps_executed") or 0) + 1
        return update

    return execute
