"""Search worker node: step_start / SearchRunner / step_end without PDF (SEARCH-01, LOOP-01)."""

from __future__ import annotations

from langgraph.config import get_stream_writer

from plan_based_researcher.agents.factory import AgentFactory
from plan_based_researcher.graph.state import GraphState

__all__ = ["make_search_node"]


def make_search_node(factory: AgentFactory):
    async def search(state: GraphState) -> dict:
        writer = get_stream_writer()
        plan = state.get("plan") or []
        idx = int(state.get("step_index") or 0)
        step = plan[idx] if 0 <= idx < len(plan) else {}
        if not isinstance(step, dict):
            step = {}
        agent = step.get("agent") or "search"
        task = step.get("task") or ""
        writer({"event": "step_start", "data": {"agent": agent, "task": task, "step_index": idx}})
        update = await factory.create("search").run(state)
        paper_ids = []
        artifacts = update.get("search_artifacts") or {}
        query_used = ""
        if isinstance(artifacts, dict):
            artifact = artifacts.get(str(idx)) or {}
            if isinstance(artifact, dict):
                query_used = str(artifact.get("query_used") or "")
                for hit in artifact.get("hits") or []:
                    if isinstance(hit, dict) and hit.get("arxiv_id"):
                        paper_ids.append(hit["arxiv_id"])
        writer({
            "event": "step_end",
            "data": {
                "agent": agent,
                "paper_ids": paper_ids,
                "pgvector": "n/a",
                "query_used": query_used,
            },
        })
        return update

    return search
