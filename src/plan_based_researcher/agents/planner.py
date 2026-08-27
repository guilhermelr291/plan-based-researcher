"""Planner runner: structured ResearchPlan, registry-validated steps (PLAN-01, THR-02)."""

from __future__ import annotations

import json

from langchain_openai import ChatOpenAI

from plan_based_researcher.agents.registry import REGISTRY, planner_prompt_abilities
from plan_based_researcher.api.schemas import ResearchPlan

__all__ = ["PlannerRunner"]


def _papers_blob(papers: object) -> str:
    if not papers:
        return "(none)"
    return json.dumps(papers, default=str)


class PlannerRunner:
    def __init__(self, api_key: str | None = None) -> None:
        kwargs: dict = {"model": REGISTRY["planner"].model}
        if api_key is not None:
            kwargs["api_key"] = api_key
        self._llm = ChatOpenAI(**kwargs).with_structured_output(ResearchPlan)

    async def run(self, state: dict) -> dict:
        query = state.get("query") or ""
        papers = state.get("papers") or []
        prompt = (
            "Produce an ordered executable plan. Each step is "
            "{agent, task, reasoning, historical}.\n"
            "Set reuse_existing_papers=True when this is a follow-up that can use "
            "papers already on the thread; otherwise False.\n"
            "Set historical=True on a step when the question needs older papers "
            "(no 5-year filter).\n\n"
            "Available agents:\n"
            f"{planner_prompt_abilities()}\n\n"
            f"Query:\n{query}\n\n"
            f"Papers already on this thread:\n{_papers_blob(papers)}"
        )
        plan = await self._llm.ainvoke(prompt)
        if not isinstance(plan, ResearchPlan):
            plan = ResearchPlan.model_validate(plan)
        for step in plan.steps:
            if step.agent not in REGISTRY:
                raise ValueError(f"invalid agent name: {step.agent}")
        return {
            "plan": [step.model_dump() for step in plan.steps],
            "last_agent": "planner",
            "reuse_existing_papers": plan.reuse_existing_papers,
        }
