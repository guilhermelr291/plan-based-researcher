"""POST /research SSE route (API-01, SSE-01, SSE-02, CAP-01)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from plan_based_researcher.api.deps import get_graph, get_settings
from plan_based_researcher.api.schemas import ResearchRequest
from plan_based_researcher.api.sse import encode_payload, encode_sse

router = APIRouter()

_SENTINEL = object()


def _initial_state(request: ResearchRequest) -> dict[str, Any]:
    return {
        "query": request.query,
        "messages": [{"role": "user", "content": request.query}],
        "papers": [],
        "plan": [],
        "step_index": 0,
        "retry_count": 0,
        "steps_executed": 0,
        "last_agent": "",
        "last_eval": {},
        "evidence_chunks": [],
        "writer_markdown": "",
        "citations": [],
        "outcome": "pending",
        "gate": {},
        "error_message": "",
        "reuse_existing_papers": False,
    }


def _custom_payload(chunk: object) -> dict | None:
    payload: object = None
    if isinstance(chunk, dict) and chunk.get("type") == "custom":
        payload = chunk.get("data")
    elif isinstance(chunk, tuple) and len(chunk) >= 2 and chunk[0] == "custom":
        payload = chunk[-1]
    if isinstance(payload, dict) and "event" in payload and "data" in payload:
        return payload
    return None


async def iter_sse(
    graph: Any,
    request: ResearchRequest,
    timeout_seconds: int,
) -> AsyncIterator[bytes]:
    config = {"configurable": {"thread_id": request.thread_id}}
    stream = None
    try:
        stream = graph.astream(
            _initial_state(request),
            config=config,
            stream_mode=["updates", "custom"],
            version="v2",
        )
        aiter = stream.__aiter__()
        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield encode_sse("insufficient", {"reason": "timeout"})
                return
            try:
                chunk = await asyncio.wait_for(
                    anext(aiter, _SENTINEL),
                    timeout=remaining,
                )
            except (TimeoutError, asyncio.TimeoutError):
                yield encode_sse("insufficient", {"reason": "timeout"})
                return
            if chunk is _SENTINEL:
                return
            payload = _custom_payload(chunk)
            if payload is None:
                continue
            try:
                yield encode_payload(payload)
            except (KeyError, TypeError, ValueError):
                continue
    except Exception as exc:
        yield encode_sse("error", {"message": str(exc)})
    finally:
        aclose = getattr(stream, "aclose", None) if stream is not None else None
        if aclose is not None:
            await aclose()


def _parse_research_request(body: object) -> ResearchRequest:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="thread_id is required")
    thread_id = body.get("thread_id")
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise HTTPException(status_code=400, detail="thread_id is required")
    query = body.get("query")
    if not isinstance(query, str):
        query = "" if query is None else str(query)
    return ResearchRequest(query=query, thread_id=thread_id.strip())


@router.post("/research")
async def research(
    request: Request,
    graph: Any = Depends(get_graph),
    settings: Any = Depends(get_settings),
) -> StreamingResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="thread_id is required") from None
    research_request = _parse_research_request(body)
    timeout_seconds = int(getattr(settings, "research_timeout_seconds", 120))
    return StreamingResponse(
        iter_sse(graph, research_request, timeout_seconds),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
