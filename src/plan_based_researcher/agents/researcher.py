"""Researcher runner: search, policy filter, ingest, numbered RAG chunks."""

from __future__ import annotations

from dataclasses import asdict, replace

from langchain_text_splitters import RecursiveCharacterTextSplitter

from plan_based_researcher.policy import Policy
from plan_based_researcher.ports.chunks import ChunkRepository, PaperRecord
from plan_based_researcher.ports.embeddings import EmbeddingPort
from plan_based_researcher.ports.papers import PaperHit, PaperPort

__all__ = ["ResearcherRunner"]

_RETRIEVE_K = 8


def _paper_ref_from_hit(hit: PaperHit) -> dict:
    return {
        "arxiv_id": hit.arxiv_id,
        "version": hit.version,
        "title": hit.title,
        "year": hit.year,
        "url": hit.url,
        "categories": list(hit.categories),
    }


def _paper_record_from_ref(ref: dict) -> PaperRecord:
    return PaperRecord(
        arxiv_id=ref["arxiv_id"],
        version=ref["version"],
        title=ref.get("title") or "",
        year=int(ref.get("year") or 0),
        url=ref.get("url") or "",
        categories=list(ref.get("categories") or []),
    )


def _unique_refs(papers: list, *, limit: int) -> list[dict]:
    selected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        key = (paper["arxiv_id"], paper["version"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(paper)
        if len(selected) >= limit:
            break
    return selected


def _current_step(state: dict) -> dict:
    plan = state.get("plan") or []
    step_index = state.get("step_index") or 0
    try:
        step_index = int(step_index)
    except (TypeError, ValueError):
        step_index = 0
    steps: list = plan.get("steps") or [] if isinstance(plan, dict) else plan
    if 0 <= step_index < len(steps):
        step = steps[step_index]
        return step if isinstance(step, dict) else {}
    return {}


def _reuse_existing(state: dict) -> bool:
    if state.get("reuse_existing_papers"):
        return True
    plan = state.get("plan")
    return bool(isinstance(plan, dict) and plan.get("reuse_existing_papers"))


class ResearcherRunner:
    def __init__(
        self,
        papers: PaperPort,
        chunks: ChunkRepository,
        embeddings: EmbeddingPort,
    ) -> None:
        self._papers = papers
        self._chunks = chunks
        self._embeddings = embeddings

    async def run(self, state: dict) -> dict:
        query = state.get("query") or ""
        step = _current_step(state)
        historical = bool(step.get("historical", False))
        task_or_query = step.get("task") or query
        existing = _unique_refs(state.get("papers") or [], limit=Policy.max_papers)
        reuse = _reuse_existing(state)
        last_eval = state.get("last_eval") or {}
        is_retry = last_eval.get("status") == "retry"
        feedback = str(last_eval.get("feedback") or "").strip()
        search_text = task_or_query
        if is_retry and feedback:
            search_text = f"{task_or_query}\n{feedback}"

        if reuse and not is_retry:
            selected = existing
        else:
            hits = await self._papers.search(
                search_text, max_results=Policy.max_papers
            )
            selected = existing[:]
            seen = {(p["arxiv_id"], p["version"]) for p in selected}
            room = Policy.max_papers - len(seen)
            for hit in hits:
                if room <= 0:
                    break
                if not Policy.is_allowlisted(hit.categories):
                    continue
                if not Policy.within_recency(
                    hit.published_at, historical=historical
                ):
                    continue
                key = (hit.arxiv_id, hit.version)
                if key in seen:
                    continue
                selected.append(_paper_ref_from_hit(hit))
                seen.add(key)
                room -= 1

        usable: list[dict] = []
        any_miss = False
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=Policy.chunk_size,
            chunk_overlap=Policy.chunk_overlap,
        )
        for ref in selected:
            record = await self._chunks.get_paper(ref["arxiv_id"], ref["version"])
            if record is None:
                any_miss = True
                text = await self._papers.load_pdf_text(
                    ref["arxiv_id"], ref["version"]
                )
                if not text.strip():
                    continue
                parts = splitter.split_text(text)
                if not parts:
                    continue
                vectors = await self._embeddings.embed_documents(parts)
                await self._chunks.upsert_paper_with_chunks(
                    _paper_record_from_ref(ref), parts, vectors
                )
            usable.append(ref)

        paper_keys = [(p["arxiv_id"], p["version"]) for p in usable]
        qvec = await self._embeddings.embed_query(search_text)
        found = await self._chunks.similarity_search(
            qvec, paper_keys, k=_RETRIEVE_K
        )
        numbered = [
            asdict(replace(chunk, n=i)) for i, chunk in enumerate(found, start=1)
        ]
        return {
            "papers": usable,
            "evidence_chunks": numbered,
            "last_agent": "researcher",
            "pgvector": "miss" if any_miss else "hit",
        }
