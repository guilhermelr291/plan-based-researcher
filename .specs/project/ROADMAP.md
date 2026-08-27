# Roadmap

**Current Milestone:** ArXiv-grounded research v1  
**Status:** Implemented (manual verification remaining)

---

## Foundation

**Goal:** FastAPI app, env config (OpenAI + Postgres), health check, Dockerized Postgres/pgvector, checkpointer `setup()`.
**Target:** App starts, DB reachable, checkpoint and vector tables exist.

### Features

**API Skeleton** - DONE

- FastAPI application and project layout
- Environment-based config (OpenAI, `DATABASE_URL`)
- Health endpoint
- Docker Compose: Postgres with pgvector only

---

## ArXiv-grounded research

**Goal:** Students get didactic, cited AI/ML answers from arXiv only, with a visible plan-based loop.
**Target:** Spec `.specs/features/arxiv-grounded-research/spec.md` verified end-to-end (API + Chainlit).
**Spec:** Approved 2026-08-26. Design approved. Tasks executed 2026-08-26 (automated tests deferred).

### Features

**ArXiv-Grounded Plan-Based Research** - IMPLEMENTED

- Domain gate; planner; orchestrator eval/retry; arXiv researcher; grounded writer
- SSE `POST /research` (`query`, `thread_id`)
- pgvector lazy ingest `(arxiv_id, version)`
- `AsyncPostgresSaver` thread state
- Chainlit steps + side-panel citations

---

## Future Considerations

- Auth, multi-user accounts, billing
- Thread TTL / delete and cross-session history UI
- Hover/JSX citation tooltips
- Writer `answer_delta` after eval pass
- arXiv TeX/HTML parsers
- Dockerize API and Chainlit
- Global semantic search over the full ingested corpus
- Human-in-the-loop plan approval
