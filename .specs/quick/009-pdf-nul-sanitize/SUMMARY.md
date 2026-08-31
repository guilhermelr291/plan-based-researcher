# Summary: 009 Strip NUL from PDF extract

**Date:** 2026-08-31
**Status:** Done

## What changed

`ArxivLoader` uses PyMuPDF `page.get_text()`, which can include U+0000. `upsert_paper_with_chunks` then fails with `PostgreSQL text fields cannot contain NUL (0x00) bytes` (trace `01a058da-c1b4-7633-befb-39b6249739c7`). Load now drops those bytes before split/embed/insert.

## Verification

- `_sanitize_pdf_text("a\\x00b") == "ab"`

## Commit

(not created — commit when asked)
