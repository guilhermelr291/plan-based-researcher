"""LangChain arXiv adapter for PaperPort (ARX-01, RUN-01)."""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlparse

from langchain_community.document_loaders import ArxivLoader
from langchain_community.retrievers import ArxivRetriever

from plan_based_researcher.ports.papers import PaperHit

_ABS_ID_RE = re.compile(
    r"(?:/abs/)?(?P<arxiv_id>\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v(?P<version>\d+))?",
    re.IGNORECASE,
)


def _parse_arxiv_id_and_version(entry_id: str) -> tuple[str, str] | None:
    if not entry_id:
        return None
    path = urlparse(entry_id).path or entry_id
    match = _ABS_ID_RE.search(path) or _ABS_ID_RE.search(entry_id)
    if match is None:
        return None
    return match.group("arxiv_id"), match.group("version") or "1"


def _as_utc_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _categories(metadata: dict[str, Any]) -> list[str]:
    raw = metadata.get("categories")
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str) and raw:
        return [raw]
    primary = metadata.get("primary_category")
    if isinstance(primary, str) and primary:
        return [primary]
    return []


def _paper_url(arxiv_id: str, metadata: dict[str, Any]) -> str:
    links = metadata.get("links")
    if isinstance(links, list):
        for href in links:
            if isinstance(href, str) and "/abs/" in href:
                return href
        for href in links:
            if isinstance(href, str) and "/pdf/" in href:
                return href
    for key in ("Entry ID", "entry_id"):
        raw = metadata.get(key)
        if isinstance(raw, str) and "/abs/" in raw:
            return raw
    return f"https://arxiv.org/abs/{arxiv_id}"


def _hit_from_doc(doc: Any) -> PaperHit | None:
    metadata = dict(getattr(doc, "metadata", None) or {})
    page_content = getattr(doc, "page_content", "") or ""
    entry_id = metadata.get("Entry ID") or metadata.get("entry_id") or ""
    parsed = _parse_arxiv_id_and_version(str(entry_id))
    if parsed is None:
        return None
    arxiv_id, version = parsed
    published_at = _as_utc_datetime(
        metadata.get("Published") or metadata.get("published_first_time")
    )
    if published_at is None:
        return None
    abstract = str(page_content or metadata.get("Summary") or "")
    return PaperHit(
        arxiv_id=arxiv_id,
        version=version,
        title=str(metadata.get("Title") or ""),
        year=published_at.year,
        url=_paper_url(arxiv_id, metadata),
        categories=_categories(metadata),
        published_at=published_at,
        abstract=abstract,
    )


def _search_sync(query: str, max_results: int) -> list[PaperHit]:
    retriever = ArxivRetriever(
        top_k_results=max_results,
        load_all_available_meta=True,
    )
    docs = retriever.invoke(query)
    hits: list[PaperHit] = []
    for doc in docs:
        hit = _hit_from_doc(doc)
        if hit is not None:
            hits.append(hit)
    return hits


def _load_pdf_text_sync(arxiv_id: str, version: str) -> str:
    loader = ArxivLoader(query=f"{arxiv_id}v{version}", load_max_docs=1)
    docs = loader.load()
    if not docs:
        return ""
    return "".join(doc.page_content or "" for doc in docs)


class ArxivPaperAdapter:
    """PaperPort backed by LangChain ArxivRetriever and ArxivLoader."""

    async def search(self, query: str, *, max_results: int) -> list[PaperHit]:
        return await asyncio.to_thread(_search_sync, query, max_results)

    async def load_pdf_text(self, arxiv_id: str, version: str) -> str:
        return await asyncio.to_thread(_load_pdf_text_sync, arxiv_id, version)
