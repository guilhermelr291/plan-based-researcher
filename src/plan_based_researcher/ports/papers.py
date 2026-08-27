"""Outbound port for arXiv paper search and PDF text loading (ARX-01)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

__all__ = ["PaperHit", "PaperPort"]


@dataclass(frozen=True, slots=True)
class PaperHit:
    arxiv_id: str
    version: str
    title: str
    year: int
    url: str
    categories: list[str]
    published_at: datetime
    abstract: str


class PaperPort(Protocol):
    async def search(self, query: str, *, max_results: int) -> list[PaperHit]: ...

    async def load_pdf_text(self, arxiv_id: str, version: str) -> str: ...
