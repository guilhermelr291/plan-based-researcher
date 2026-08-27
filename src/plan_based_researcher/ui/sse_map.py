"""Parse research SSE frames and map citations to side-panel labels (UI-02)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from plan_based_researcher.api.sse import SSE_EVENTS


def side_panel_texts(citations: list[dict]) -> list[tuple[str, str]]:
    """Return ``("[n]", excerpt)`` pairs for Chainlit side-panel ``cl.Text``."""
    items: list[tuple[str, str]] = []
    for citation in citations:
        n = citation.get("n")
        if n is None:
            continue
        items.append((f"[{n}]", _citation_excerpt(citation)))
    return items


async def iter_sse_frames(lines: AsyncIterator[str]) -> AsyncIterator[tuple[str, dict]]:
    """Yield ``(event, data)`` from SSE lines; dispatch on each blank line."""
    buffer: list[str] = []
    async for raw in lines:
        line = raw.rstrip("\r")
        if line == "":
            parsed = _parse_frame(buffer)
            buffer = []
            if parsed is not None:
                yield parsed
            continue
        buffer.append(line)
    parsed = _parse_frame(buffer)
    if parsed is not None:
        yield parsed


def _citation_excerpt(citation: dict) -> str:
    excerpt = str(citation.get("excerpt") or "")
    arxiv_id = citation.get("arxiv_id")
    if not arxiv_id:
        return excerpt
    title = citation.get("title") or ""
    year = citation.get("year")
    header = f"arXiv:{arxiv_id}"
    if title:
        header = f"{header} — {title}"
    if year is not None and year != "":
        header = f"{header} ({year})"
    parts = [header]
    url = citation.get("url")
    if url:
        parts.append(str(url))
    if excerpt:
        parts.append(excerpt)
    return "\n".join(parts)


def _field_value(line: str, prefix: str) -> str:
    value = line[len(prefix) :]
    if value.startswith(" "):
        return value[1:]
    return value


def _parse_frame(lines: list[str]) -> tuple[str, dict] | None:
    event = ""
    data_parts: list[str] = []
    for line in lines:
        if not line or line.startswith(":"):
            continue
        if line.startswith("event:"):
            event = _field_value(line, "event:")
        elif line.startswith("data:"):
            data_parts.append(_field_value(line, "data:"))
    if event not in SSE_EVENTS:
        return None
    raw = "\n".join(data_parts)
    if not raw:
        return event, {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return event, {"raw": raw}
    if isinstance(payload, dict):
        return event, payload
    return event, {"value": payload}
