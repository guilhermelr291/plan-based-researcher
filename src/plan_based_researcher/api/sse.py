"""SSE frame mapper: spec event names only (SSE-01, SSE-02)."""

from __future__ import annotations

import json

SSE_EVENTS: frozenset[str] = frozenset(
    {
        "gate",
        "plan",
        "step_start",
        "step_end",
        "eval",
        "answer_complete",
        "done",
        "insufficient",
        "error",
    }
)


def encode_sse(event: str, data: object) -> bytes:
    """Encode one SSE frame as UTF-8 ``event:`` / ``data:`` bytes."""
    if event not in SSE_EVENTS:
        raise ValueError(f"unknown SSE event: {event!r}")
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def encode_payload(payload: dict) -> bytes:
    """Encode a LangGraph ``{event, data}`` dict to an SSE frame."""
    return encode_sse(payload["event"], payload["data"])
