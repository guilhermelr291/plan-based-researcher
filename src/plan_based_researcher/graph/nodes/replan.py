"""Replan remaining graph node: suffix-only rewrite, prefix packed (REPLAN-01, REPLAN-02)."""

from __future__ import annotations

from langgraph.config import get_stream_writer

from plan_based_researcher.agents.factory import AgentFactory
from plan_based_researcher.graph.state import GraphState, merge_hole_tasks


def _passed_set(state: GraphState) -> set[int]:
    passed: set[int] = set()
    for i in state.get("passed_steps") or []:
        try:
            passed.add(int(i))
        except (TypeError, ValueError):
            continue
    return passed


def _has_writer(steps: list) -> bool:
    for step in steps:
        if isinstance(step, dict) and step.get("agent") == "writer":
            return True
    return False


def _lookup_keyed(raw: object, index: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    item = raw.get(str(index))
    if item is None:
        item = raw.get(index)
    return item if isinstance(item, dict) else None


def _remap_keyed(raw: object, old_indices: list[int]) -> dict:
    """Copy records from old plan indices onto new prefix indices 0..n-1."""
    remapped: dict = {}
    for new_index, old_index in enumerate(old_indices):
        item = _lookup_keyed(raw, old_index)
        if item is None:
            continue
        copied = dict(item)
        copied["step_index"] = new_index
        remapped[str(new_index)] = copied
    return remapped


def _leftover_search_holes(plan: list, passed_set: set[int]) -> list[dict]:
    extras: list[dict] = []
    for index, step in enumerate(plan):
        if index in passed_set or not isinstance(step, dict):
            continue
        if step.get("agent") != "search":
            continue
        task = str(step.get("task") or "").strip()
        if task:
            extras.append({"task": task, "reason": "unpassed"})
    return extras


def _remap_ingest(ingest: object, old_indices: list[int]) -> dict | None:
    if not isinstance(ingest, dict):
        return None
    old_to_new = {old: new for new, old in enumerate(old_indices)}
    gaps: list[int] = []
    for raw in ingest.get("gap_step_indices") or []:
        try:
            old_gap = int(raw)
        except (TypeError, ValueError):
            continue
        if old_gap in old_to_new:
            gaps.append(old_to_new[old_gap])
    remapped = dict(ingest)
    remapped["gap_step_indices"] = gaps
    return remapped


def make_replan_node(factory: AgentFactory):
    async def replan(state: GraphState) -> dict:
        writer = get_stream_writer()
        try:
            result = await factory.create("planner").replan_remaining(state)
        except Exception as exc:
            return {"outcome": "error", "error_message": str(exc)}

        plan = state.get("plan") or []
        if not isinstance(plan, list):
            plan = []
        passed_set = _passed_set(state)
        old_indices = [i for i in range(len(plan)) if i in passed_set]
        prefix = [plan[i] for i in old_indices]
        suffix = result.get("plan") or []
        if not isinstance(suffix, list):
            suffix = []
        new_plan = prefix + suffix

        writer({
            "event": "plan",
            "data": {
                "steps": suffix,
            },
        })

        update: dict = {
            "plan": new_plan,
            "passed_steps": list(range(len(prefix))),
            "step_index": len(prefix),
            "retry_counts": {},
            "retry_count": 0,
            "replan_used": True,
            "last_agent": result.get("last_agent") or "planner",
            "outcome": "pending",
            "search_artifacts": _remap_keyed(state.get("search_artifacts"), old_indices),
            "eval_by_step": _remap_keyed(state.get("eval_by_step"), old_indices),
            "hole_tasks": merge_hole_tasks(
                state.get("hole_tasks"),
                _leftover_search_holes(plan, passed_set),
            ),
        }
        remapped_ingest = _remap_ingest(state.get("retrieve_ingest"), old_indices)
        if remapped_ingest is not None:
            update["retrieve_ingest"] = remapped_ingest
        if not suffix or not _has_writer(suffix):
            update["outcome"] = "insufficient"
        return update

    return replan
