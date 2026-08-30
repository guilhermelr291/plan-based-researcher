"""Execute node: sequential retrieve/writer via factory (LOOP-01, WRITE-01, PAT-04)."""

from __future__ import annotations

from langgraph.config import get_stream_writer

from plan_based_researcher.agents.factory import AgentFactory
from plan_based_researcher.graph.state import GraphState

__all__ = ["make_execute_node"]


def make_execute_node(factory: AgentFactory):
    async def execute(state: GraphState) -> dict:
        writer = get_stream_writer()
        plan = state.get("plan") or []
        passed = set(state.get("passed_steps") or [])
        idx = None
        for i in range(len(plan)):
            if i not in passed:
                idx = i
                break
        if idx is None:
            idx = int(state.get("step_index") or 0)
        step = plan[idx] if 0 <= idx < len(plan) else {}
        if not isinstance(step, dict):
            step = {}
        agent = step.get("agent") or ""
        task = step.get("task") or ""
        writer({"event": "step_start", "data": {"agent": agent, "task": task, "step_index": idx}})
        if agent == "search":
            update = {
                "outcome": "error",
                "error_message": "search is not executed here",
            }
        elif agent not in ("retrieve", "writer"):
            update = {
                "outcome": "error",
                "error_message": f"unknown agent: {agent!r}",
            }
        else:
            try:
                update = await factory.create(agent).run(state)
            except KeyError as exc:
                update = {
                    "outcome": "error",
                    "error_message": str(exc),
                }
        papers = update.get("papers") or state.get("papers") or []
        paper_ids = []
        for p in papers:
            if isinstance(p, dict) and p.get("arxiv_id"):
                paper_ids.append(p["arxiv_id"])
        pgvector = update.get("pgvector") or "hit"
        query_used = update.get("retrieve_query_used") or ""
        writer({
            "event": "step_end",
            "data": {
                "agent": agent,
                "paper_ids": paper_ids,
                "pgvector": pgvector,
                "query_used": query_used,
            },
        })
        update["steps_executed"] = (state.get("steps_executed") or 0) + 1
        return update

    return execute
