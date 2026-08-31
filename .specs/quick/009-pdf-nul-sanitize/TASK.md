# Quick Task 009: Strip NUL bytes from arXiv PDF text

**Date:** 2026-08-31
**Status:** Done

## Description

PyMuPDF `get_text()` (via `ArxivLoader`) can emit `\x00`; Postgres TEXT cannot. Strip NUL after load so retrieve upsert does not raise `psycopg.DataError`.

## Files Changed

- `src/plan_based_researcher/adapters/arxiv.py` — `_sanitize_pdf_text` on concatenated page content

## Verification

- [x] `"a\\x00b"` sanitizes to `"ab"` with no NUL remaining

## Commit

(not created — commit when asked)
