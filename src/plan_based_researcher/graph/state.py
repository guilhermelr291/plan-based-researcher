"""LangGraph state schema and paper-list reducer (THR-01, ARX-04)."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages

from plan_based_researcher.policy import Policy

__all__ = ["EvidenceChunk", "GraphState", "PaperRef", "merge_papers"]


class PaperRef(TypedDict):
    arxiv_id: str
    version: str
    title: str
    year: int
    url: str
    categories: list[str]


class EvidenceChunk(TypedDict):
    chunk_id: str
    n: int
    arxiv_id: str
    version: str
    title: str
    year: int
    url: str
    excerpt: str


def merge_papers(
    existing: list[PaperRef] | None,
    new: list[PaperRef] | None,
) -> list[PaperRef]:
    """Union papers by (arxiv_id, version), last write wins, trim to Policy.max_papers."""
    merged: dict[tuple[str, str], PaperRef] = {}
    for paper in (existing or []) + (new or []):
        merged[(paper["arxiv_id"], paper["version"])] = paper
    return list(merged.values())[: Policy.max_papers]


class GraphState(TypedDict):
    query: str
    messages: Annotated[list, add_messages]
    papers: Annotated[list[PaperRef], merge_papers]
    plan: list[dict]
    step_index: int
    retry_count: int
    steps_executed: int
    last_agent: str
    last_eval: dict
    evidence_chunks: list[EvidenceChunk]
    writer_markdown: str
    citations: list[dict]
    outcome: Literal["pending", "refused", "done", "insufficient", "error"]
    gate: dict
    error_message: str
