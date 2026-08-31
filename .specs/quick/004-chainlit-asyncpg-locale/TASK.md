# Quick Task 004: Chainlit UI crash and pt-BR markdown warning

**Date:** 2026-08-30
**Status:** Done

## Description

Stop Chainlit from treating the API `DATABASE_URL` as its persistence layer (missing `asyncpg` crash) and add a pt-BR welcome markdown so the locale warning goes away.

## Files Changed

- `src/plan_based_researcher/ui/app.py` — drop `DATABASE_URL` after Chainlit loads `.env`
- `chainlit.md` — project welcome (English)
- `chainlit_pt-BR.md` — project welcome (pt-BR)

## Verification

- [x] `GET /project/settings?language=pt-BR` returns HTTP 200
- [x] Chainlit log has no `ModuleNotFoundError: asyncpg`
- [x] Chainlit log has no `Translated markdown file for pt-BR not found`

## Commit

(not created — commit when asked)
