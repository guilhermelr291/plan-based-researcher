"""Agent name → abilities, model, and tools (PAT-02). Planner prompt is built from this map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Role = Literal["gate", "planner", "researcher", "writer"]

_PLANNER_WRITER_MODEL = "gpt-5.1"
_MINI_MODEL = "gpt-5-mini"


@dataclass(frozen=True, slots=True)
class AgentSpec:
    name: str
    abilities: str
    model: str
    tools: tuple[str, ...]
    role: Role


REGISTRY: dict[str, AgentSpec] = {
    "gate": AgentSpec(
        name="gate",
        abilities=(
            "Decide if the student query is AI/ML in-domain. Never search arXiv."
        ),
        model=_MINI_MODEL,
        tools=(),
        role="gate",
    ),
    "planner": AgentSpec(
        name="planner",
        abilities=(
            "Produce an ordered plan of {agent, task, reasoning}. "
            "May mark historical steps. For follow-ups, set reuse_existing_papers "
            "when the thread already has the needed papers."
        ),
        model=_PLANNER_WRITER_MODEL,
        tools=(),
        role="planner",
    ),
    "researcher": AgentSpec(
        name="researcher",
        abilities=(
            "Search/load arXiv papers in the category allowlist, retrieve numbered "
            "chunks. Honor reuse_existing_papers (skip search)."
        ),
        model=_MINI_MODEL,
        tools=("arxiv_search", "arxiv_load"),
        role="researcher",
    ),
    "writer": AgentSpec(
        name="writer",
        abilities=(
            "Write a didactic student answer citing only provided [n] chunks. "
            "State contradictions. No extra sources."
        ),
        model=_PLANNER_WRITER_MODEL,
        tools=(),
        role="writer",
    ),
}


def planner_prompt_abilities() -> str:
    """Concatenate every registry agent name and abilities for the planner prompt (PLAN-01)."""
    return "\n".join(
        f"{spec.name}: {spec.abilities}" for spec in REGISTRY.values()
    )
