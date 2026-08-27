"""Agent factory: registry name → runner lookup (PAT-02)."""

from __future__ import annotations

from typing import Protocol

from plan_based_researcher.agents.gate import GateRunner
from plan_based_researcher.agents.planner import PlannerRunner
from plan_based_researcher.agents.researcher import ResearcherRunner
from plan_based_researcher.agents.writer import WriterRunner
from plan_based_researcher.ports.chunks import ChunkRepository
from plan_based_researcher.ports.embeddings import EmbeddingPort
from plan_based_researcher.ports.papers import PaperPort


class AgentRunner(Protocol):
    async def run(self, state: dict) -> dict: ...


class AgentFactory:
    """Bind runners once; dispatch by registry name, not if/elif."""

    def __init__(
        self,
        papers: PaperPort,
        chunks: ChunkRepository,
        embeddings: EmbeddingPort,
        api_key: str | None = None,
    ) -> None:
        self._runners: dict[str, AgentRunner] = {
            "gate": GateRunner(api_key=api_key),
            "planner": PlannerRunner(api_key=api_key),
            "researcher": ResearcherRunner(papers, chunks, embeddings),
            "writer": WriterRunner(api_key=api_key),
        }

    def create(self, name: str) -> AgentRunner:
        try:
            return self._runners[name]
        except KeyError:
            raise KeyError(f"unknown agent: {name}") from None
