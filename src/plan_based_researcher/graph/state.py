"""LangGraph state schema and reducers (THR-01, ARX-04, LOOP-01, SEARCH-01, REPLAN-01, CAP-02, ADM-03, RETR-04)."""

from __future__ import annotations

from typing import Annotated, Literal, NotRequired, TypedDict

from langgraph.graph.message import add_messages

from plan_based_researcher.policy import Policy

__all__ = [
    "EvidenceChunk",
    "GraphState",
    "PaperRef",
    "RankedKey",
    "RetrieveIngestReport",
    "SearchArtifact",
    "SearchHit",
    "merge_eval_by_step",
    "merge_papers",
    "merge_search_artifacts",
]


class PaperRef(TypedDict):
    arxiv_id: str
    version: str
    title: str
    year: int
    url: str
    categories: list[str]


class SearchHit(TypedDict):
    arxiv_id: str
    version: str
    title: str
    year: int
    url: str
    categories: list[str]
    abstract: str


class RankedKey(TypedDict):
    arxiv_id: str
    version: str


class SearchArtifact(TypedDict):
    step_index: int
    query_used: str
    hits: list[SearchHit]
    ranked_keys: NotRequired[list[RankedKey]]


class RetrieveIngestReport(TypedDict):
    case: Literal["t1", "t2a", "t3"]
    gap_step_indices: list[int]
    walked: bool


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


def merge_search_artifacts(
    existing: dict[str, SearchArtifact] | None,
    new: dict[str, SearchArtifact] | None,
) -> dict[str, SearchArtifact]:
    """Merge search artifacts by step key, last write wins."""
    return {**(existing or {}), **(new or {})}


def merge_eval_by_step(
    existing: dict[str, dict] | None,
    new: dict[str, dict] | None,
) -> dict[str, dict]:
    """Merge per-step eval records by step key, last write wins (LOOP-02)."""
    return {**(existing or {}), **(new or {})}


class GraphState(TypedDict):
    query: str
    messages: Annotated[list, add_messages]
    papers: Annotated[list[PaperRef], merge_papers]
    plan: list[dict]
    step_index: int
    passed_steps: list[int]
    retry_counts: dict[str, int]
    retry_count: int
    replan_used: bool
    steps_executed: int
    search_artifacts: Annotated[dict[str, SearchArtifact], merge_search_artifacts]
    last_agent: str
    last_eval: dict
    eval_by_step: Annotated[dict[str, dict], merge_eval_by_step]
    retrieve_query_used: str
    retrieve_ingest: RetrieveIngestReport
    evidence_chunks: list[EvidenceChunk]
    writer_markdown: str
    citations: list[dict]
    outcome: Literal["pending", "refused", "done", "insufficient", "error"]
    # SPEC_DEVIATION: eval_next is not in the design TypedDict.
    # Reason: LangGraph drops undeclared keys; evaluate→replan routing needs a channel.
    eval_next: Literal["dispatch", "replan", "finalize"]
    gate: dict
    error_message: str
    reuse_existing_papers: bool
