# Quick Task 005: Pin arxiv below 4.0 for LangChain search

**Date:** 2026-08-30
**Status:** Done

## Description

Stop search from crashing with `AttributeError: 'Search' object has no attribute 'results'` by pinning `arxiv` to a version LangChain Community still supports.

## Files Changed

- `pyproject.toml` — constrain `arxiv>=2.2.0,<4`
- `uv.lock` — resolve to arxiv 3.0.0

## Verification

- [x] Installed `arxiv` is `3.0.0`; `Search.results` and `Result.download_pdf` exist
- [x] LangChain `ArxivAPIWrapper.arxiv_search(...).results()` returns an iterator (no `AttributeError`)
- [ ] Live `ArxivRetriever.invoke` against export.arxiv.org — not re-run here after the API returned HTTP 429 from smoke-test traffic; restart the API process so it loads arxiv 3.0.0

## Commit

(not created — commit when asked)
