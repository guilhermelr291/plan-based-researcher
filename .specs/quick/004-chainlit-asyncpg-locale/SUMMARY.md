# Summary: 004 Chainlit asyncpg crash and pt-BR markdown

**Date:** 2026-08-30
**Status:** Done

## What changed

Chainlit was reading this project's `DATABASE_URL` (meant for FastAPI + psycopg/pgvector) and trying to start `ChainlitDataLayer`, which imports `asyncpg`. The UI process now drops `DATABASE_URL` after Chainlit loads `.env`. Welcome markdown exists for `en` (`chainlit.md`) and `pt-BR` (`chainlit_pt-BR.md`).

## Verification

`GET http://127.0.0.1:8000/project/settings?language=pt-BR` → HTTP 200, `dataPersistence: false`, Portuguese markdown body. No `asyncpg` traceback. No "Translated markdown file for pt-BR not found" warning.

## Commit

Not created.
