"""Postgres papers/chunks store; RAG is scoped to selected (arxiv_id, version) keys."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from pgvector import Vector
from pgvector.psycopg import register_vector_async
from psycopg_pool import AsyncConnectionPool

from plan_based_researcher.ports.chunks import EvidenceChunk, PaperRecord

_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS papers (
  arxiv_id TEXT NOT NULL,
  version TEXT NOT NULL,
  title TEXT NOT NULL,
  year INT NOT NULL,
  url TEXT NOT NULL,
  categories TEXT[] NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (arxiv_id, version)
);

CREATE TABLE IF NOT EXISTS chunks (
  chunk_id UUID PRIMARY KEY,
  arxiv_id TEXT NOT NULL,
  version TEXT NOT NULL,
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536) NOT NULL,
  UNIQUE (arxiv_id, version, chunk_index),
  FOREIGN KEY (arxiv_id, version) REFERENCES papers (arxiv_id, version)
);

CREATE INDEX IF NOT EXISTS chunks_papers_idx ON chunks (arxiv_id, version);
"""

_GET_PAPER_SQL = """
SELECT arxiv_id, version, title, year, url, categories
FROM papers
WHERE arxiv_id = %s AND version = %s
"""

_UPSERT_PAPER_SQL = """
INSERT INTO papers (arxiv_id, version, title, year, url, categories)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (arxiv_id, version) DO UPDATE SET
  title = EXCLUDED.title,
  year = EXCLUDED.year,
  url = EXCLUDED.url,
  categories = EXCLUDED.categories
"""

_DELETE_CHUNKS_SQL = """
DELETE FROM chunks WHERE arxiv_id = %s AND version = %s
"""

_INSERT_CHUNK_SQL = """
INSERT INTO chunks (chunk_id, arxiv_id, version, chunk_index, content, embedding)
VALUES (%s, %s, %s, %s, %s, %s)
"""

_SIMILARITY_SEARCH_SQL = """
SELECT
  c.chunk_id,
  c.arxiv_id,
  c.version,
  p.title,
  p.year,
  p.url,
  c.content
FROM chunks AS c
JOIN papers AS p
  ON p.arxiv_id = c.arxiv_id AND p.version = c.version
WHERE (c.arxiv_id, c.version) IN (
  SELECT * FROM unnest(%s::text[], %s::text[]) AS t(arxiv_id, version)
)
ORDER BY c.embedding <=> %s
LIMIT %s
"""


def _schema_statements(sql: str) -> list[str]:
    return [part.strip() for part in sql.split(";") if part.strip()]


def _paper_from_row(row: Mapping[str, Any]) -> PaperRecord:
    return PaperRecord(
        arxiv_id=str(row["arxiv_id"]),
        version=str(row["version"]),
        title=str(row["title"]),
        year=int(row["year"]),
        url=str(row["url"]),
        categories=list(row["categories"]),
    )


def _chunk_from_row(row: Mapping[str, Any]) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=str(row["chunk_id"]),
        arxiv_id=str(row["arxiv_id"]),
        version=str(row["version"]),
        title=str(row["title"]),
        year=int(row["year"]),
        url=str(row["url"]),
        excerpt=str(row["content"]),
        n=0,
    )


class PgChunkRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def ensure_schema(self) -> None:
        async with self._pool.connection() as conn:
            for statement in _schema_statements(_SCHEMA_SQL):
                await conn.execute(statement)

    async def get_paper(self, arxiv_id: str, version: str) -> PaperRecord | None:
        async with self._pool.connection() as conn:
            await register_vector_async(conn)
            cur = await conn.execute(_GET_PAPER_SQL, (arxiv_id, version))
            row = await cur.fetchone()
        if row is None:
            return None
        return _paper_from_row(row)

    async def upsert_paper_with_chunks(
        self,
        paper: PaperRecord,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError(
                "chunks and embeddings must have the same length "
                f"({len(chunks)} != {len(embeddings)})"
            )
        rows = [
            (
                uuid4(),
                paper.arxiv_id,
                paper.version,
                index,
                content,
                Vector(embedding),
            )
            for index, (content, embedding) in enumerate(zip(chunks, embeddings))
        ]
        async with self._pool.connection() as conn:
            await register_vector_async(conn)
            await conn.execute(
                _UPSERT_PAPER_SQL,
                (
                    paper.arxiv_id,
                    paper.version,
                    paper.title,
                    paper.year,
                    paper.url,
                    paper.categories,
                ),
            )
            await conn.execute(_DELETE_CHUNKS_SQL, (paper.arxiv_id, paper.version))
            if rows:
                async with conn.cursor() as cur:
                    await cur.executemany(_INSERT_CHUNK_SQL, rows)

    async def similarity_search(
        self,
        query_embedding: list[float],
        paper_keys: list[tuple[str, str]],
        k: int,
    ) -> list[EvidenceChunk]:
        if not paper_keys:
            return []
        ids = [key[0] for key in paper_keys]
        vers = [key[1] for key in paper_keys]
        async with self._pool.connection() as conn:
            await register_vector_async(conn)
            cur = await conn.execute(
                _SIMILARITY_SEARCH_SQL,
                (ids, vers, Vector(query_embedding), k),
            )
            rows = await cur.fetchall()
        return [_chunk_from_row(row) for row in rows]
