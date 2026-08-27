"""Named lookup for arXiv search/load via PaperPort (PAT-03, ARX-01)."""

from typing import Literal

from plan_based_researcher.ports.papers import PaperPort

__all__ = ["ToolName", "ToolRegistry"]

ToolName = Literal["arxiv_search", "arxiv_load"]


class ToolRegistry:
    def __init__(self, papers: PaperPort) -> None:
        self._papers = papers

    def get(self, name: str) -> PaperPort:
        if name not in ("arxiv_search", "arxiv_load"):
            raise KeyError(name)
        return self._papers
