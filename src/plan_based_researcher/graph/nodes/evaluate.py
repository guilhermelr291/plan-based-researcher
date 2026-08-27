"""Evaluate node: pick strategy by last_agent; retry, advance, or fail (ORCH-01–03, CAP-01)."""

from __future__ import annotations

from langgraph.config import get_stream_writer

from plan_based_researcher.eval.strategies import ResearchEvalStrategy, WriterEvalStrategy
from plan_based_researcher.graph.state import GraphState
from plan_based_researcher.policy import Policy

__all__ = ["make_evaluate_node"]


def make_evaluate_node(
    research_eval: ResearchEvalStrategy,
    writer_eval: WriterEvalStrategy,
):
    async def evaluate(state: GraphState) -> dict:
        writer = get_stream_writer()
        last_agent = state.get("last_agent") or ""
        strategy = writer_eval if last_agent == "writer" else research_eval
        result = await strategy.evaluate(state)

        writer({
            "event": "eval",
            "data": {
                "status": result.status,
                "feedback": result.feedback,
                "agent": last_agent,
            },
        })

        update: dict = {"last_eval": result.model_dump()}

        if result.status == "retry":
            retry_count = (state.get("retry_count") or 0) + 1
            update["retry_count"] = retry_count
            if retry_count > Policy.max_retries_per_step:
                update["outcome"] = "insufficient"
        elif result.status == "fail":
            update["outcome"] = "insufficient"
        elif result.status == "pass":
            update["retry_count"] = 0
            if last_agent == "writer":
                update["outcome"] = "done"
            else:
                step_index = (state.get("step_index") or 0) + 1
                update["step_index"] = step_index
                plan = state.get("plan") or []
                if step_index >= len(plan):
                    update["outcome"] = "insufficient"

        outcome = update.get("outcome") or state.get("outcome") or "pending"
        if (state.get("steps_executed") or 0) >= Policy.max_steps and outcome == "pending":
            update["outcome"] = "insufficient"

        return update

    return evaluate
