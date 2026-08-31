# Summary: 005 Pin arxiv below 4.0 for LangChain search

**Date:** 2026-08-30
**Status:** Done

## What changed

`langchain-community` 0.4.2 still calls `arxiv.Search(...).results()` and `Result.download_pdf()`. Those APIs were removed in `arxiv` 4.0, which uv had resolved from `arxiv>=2.2.0`. The constraint is now `arxiv>=2.2.0,<4` (lock: 3.0.0) so search and PDF load keep working through the existing adapter.

`uv sync` could not delete leftover `lxml` while uvicorn held the `.pyd`; arxiv 3.0.0 was installed with `uv pip install`. After stopping the API/UI, run `uv sync` to drop unused `lxml`.

## Verification

`Search.results()` no longer raises `AttributeError`. A live retriever call was not completed in this session because export.arxiv.org returned 429 after earlier smoke requests.

## Commit

Not created.
