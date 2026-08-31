# Quick Task 006: Shared arXiv Client and request lock

**Date:** 2026-08-30
**Status:** Done

## Description

Stop parallel search waves from bursting `export.arxiv.org` by using one shared `arxiv.Client` (`page_size=8`, `delay_seconds=3`) and a process-wide lock of one API call at a time, without changing LangGraph `Send("search")`.

## Files Changed

- `src/plan_based_researcher/adapters/arxiv.py` — shared Client, asyncio lock around search and PDF load

## Verification

- [x] Shared client is `page_size=8` and `delay_seconds=3`
- [x] Concurrent `ArxivPaperAdapter.search` / `load_pdf_text` calls do not overlap (mocked I/O)
- [x] `dispatch.py` still fans out with `Send("search")`
- [x] `_hit_from_result` maps `arxiv.Result` to `PaperHit` (`2106.09685v2`)

## Commit

(pending)
