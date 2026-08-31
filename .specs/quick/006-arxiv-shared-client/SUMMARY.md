# Summary: 006 Shared arXiv Client and request lock

**Date:** 2026-08-30
**Status:** Done

## What changed

Search no longer goes through `ArxivRetriever` / `Search.results()`, which constructed a new `Client` (default `page_size=100`) per call. The adapter now uses one module-level `arxiv.Client(page_size=8, delay_seconds=3.0)` and an `asyncio.Lock` around both `search` and `load_pdf_text`. LangGraph still `Send`s search steps in parallel; HTTP is queued in the adapter.

PDF load still uses `ArxivLoader` (its own Client) but waits on the same lock so it cannot overlap a search.

## Verification

- `_CLIENT.page_size == 8`, `delay_seconds == 3.0`
- Three concurrent adapter calls (two searches + one PDF) ran strictly one after another
- `dispatch.py` still uses `Send("search")`
- Fake `arxiv.Result` maps to `PaperHit` `2106.09685` v2

## Commit

(pending)
