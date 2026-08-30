"""Chunk persistence port: identity by (arxiv_id, version); RAG scoped to selected papers."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PaperRecord:
    arxiv_id: str
    version: str
    title: str
    year: int
    url: str
    categories: list[str]


@dataclass(frozen=True, slots=True)
class EvidenceChunk:
    chunk_id: str
    arxiv_id: str
    version: str
    title: str
    year: int
    url: str
    excerpt: str
    n: int = 0


class ChunkRepository(Protocol):
    async def get_paper(self, arxiv_id: str, version: str) -> PaperRecord | None: ...

    async def upsert_paper_with_chunks(
        self,
        paper: PaperRecord,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None: ...

    async def similarity_search(
        self,
        query_embedding: list[float],
        paper_keys: list[tuple[str, str]],
        k: int,
    ) -> list[EvidenceChunk]: ...

    async def list_chunks(
        self,
        paper_keys: list[tuple[str, str]],
    ) -> list[EvidenceChunk]: ...
