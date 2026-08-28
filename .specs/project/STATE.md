# State

**Last Updated:** 2026-08-27
**Current Work:** Feature `orchestrator-eval-replan` — tasks draft pending user approval (`.specs/features/orchestrator-eval-replan/tasks.md`). Spec and design approved. v1 UAT still pending (B-001).

---

## Recent Decisions (Last 60 days)

### AD-001: Plan-based multi-agent researcher (2026-08-25)

**Decision:** Build an AI researcher where a planner agent generates the plan and an orchestrator loop assigns, evaluates, and retries or advances each step.
**Reason:** Plan-based control with per-step evaluation is the core product approach.
**Trade-off:** More moving parts than a single LLM call; slower and more token-heavy.
**Impact:** LangGraph graph is a loop around execute + evaluate, not a linear chain only.

### AD-002: v1 is backend-only (2026-08-25) — SUPERSEDED by AD-008

**Decision:** v1 ships FastAPI + LangGraph only.
**Reason:** Prove the agent loop before investing in UI.
**Trade-off:** No user-facing product until a client exists.
**Impact:** Superseded: Chainlit is in v1 as HTTP client of the API.

### AD-003: Stack — Python, FastAPI, LangChain, LangGraph, OpenAI, Tavily (2026-08-25) — SUPERSEDED by AD-005

**Decision:** OpenAI for LLM, Tavily for search.
**Reason:** User-selected at project init.
**Trade-off:** Tied to those vendors.
**Impact:** Superseded: Tavily removed; evidence is arXiv only; Postgres/pgvector added.

### AD-004: Project language is English (2026-08-25)

**Decision:** All project artifacts (code, docs, comments, API, prompts) are in English.
**Reason:** User requirement.
**Trade-off:** None material.
**Impact:** Specs, identifiers, and prompts stay in English. Student-facing answers follow the query language.

### AD-005: ArXiv-only AI/ML student researcher (2026-08-25)

**Decision:** Product domain is AI/ML forever. Evidence is arXiv only (allowlist `cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`, `cs.NE`, `cs.RO`, `stat.ML`). Audience is students: didactic structure, every technical claim cited. Prefer papers from the last 5 years unless the planner marks a historical step.
**Reason:** Grill-me; Tavily/web cannot satisfy “papers only.”
**Trade-off:** No blogs, docs, or non-arXiv venues; keyword arXiv search is weaker than a semantic corpus.
**Impact:** Drop Tavily. Researcher uses LangChain arXiv tools + `ArxivLoader` PDFs.

### AD-006: Agent roster and models (2026-08-25)

**Decision:** Gate → Planner → Orchestrator/Evaluator loop → Researcher → Writer. Planner and Writer: `gpt-5.1`. Gate, Orchestrator, Researcher: `gpt-5-mini`. Embeddings: `text-embedding-3-small`. Caps: `max_steps=8`, `max_retries_per_step=2`, `max_papers=8`, timeout ~2 min. Splitter 500/100.
**Reason:** Strong model on plan/write; cheap model on high-volume gate/eval/tools.
**Trade-off:** Eval quality vs cost; 2 min may cut long PDF ingest.
**Impact:** Config keys and node implementations follow this split.

### AD-007: Grounded generation (2026-08-25)

**Decision:** Format chunks as `[n]` before the Writer. Writer may cite only those indices. Response is markdown plus `citations[]` (id, title, year, url, excerpt, chunk_id). Contradictions must be stated. No `answer_delta`; `answer_complete` only after Writer eval passes.
**Reason:** Student must inspect passages; streaming unvalidated prose breaks grounding.
**Trade-off:** Answer appears all at once; steps still stream.
**Impact:** Orchestrator Writer checklist is normative. Chainlit maps `[n]` to side-panel `cl.Text`.

### AD-008: SSE API + Chainlit on host (2026-08-25)

**Decision:** Single async `POST /research` (`text/event-stream`). Body `{ query, thread_id }`. Chainlit on host (port 8000 assumed) calls API on host (port 8001 assumed). Only Postgres/pgvector in Docker. No auth.
**Reason:** One contract for tests and UI; stream progress without exposing ungrounded text.
**Trade-off:** Tests must parse SSE; two local processes.
**Impact:** No sync JSON research route. Chainlit does not import the graph.

### AD-009: pgvector paper store + AsyncPostgresSaver (2026-08-25)

**Decision:** Same Postgres: pgvector chunks unique on `(arxiv_id, version)` (lazy download) and LangGraph `AsyncPostgresSaver` for current-chat graph state (messages, papers, plan, last chunks). RAG only over papers selected for the thread/query, not the whole library. Missing `thread_id` → 400. Threads are not deleted in v1. Follow-up: Planner chooses reuse vs new arXiv search. Sync PDF/arXiv I/O via `asyncio.to_thread`.
**Reason:** Avoid re-download; resume chat without `prior_papers` in the client body.
**Trade-off:** DB grows; anonymous `thread_id` is not a user account.
**Impact:** API is not stateless. `setup()` on startup. Client must persist `thread_id` for follow-up.

### AD-010: Growth patterns — registry/factory, outbound ports, no HTTP adapters (2026-08-26)

**Decision:** Structure the app as: LangGraph-only orchestrator; agent registry + factory; tool registry; plan interpreter; eval strategies with result types; typed state + reducers; compile graph once in FastAPI lifespan; outbound ports for arXiv and pgvector only; chunk repository; named policy objects; SSE via FastAPI `StreamingResponse` plus a mapper function; DI via `Depends`. Do not wrap FastAPI or Chainlit in adapter classes. Chainlit remains an HTTP client.
**Reason:** User confirmed hexagonal “edge adapters” are jargon, not extra wrappers; SSE is native FastAPI; registry/factory are for agents/tools so the planner prompt and dispatch share one source of truth.
**Trade-off:** Slightly more modules up front vs a single script of nodes.
**Impact:** Design and tasks must follow `.specs/features/arxiv-grounded-research/context.md` (PAT-01–PAT-12).

### AD-011: Semantic eval, 1 retry, 1 remaining replan (2026-08-27)

**Decision:** Orchestrator interprets a variable plan of `search` / `retrieve` / `writer`. Eval is semantic and artifact-specific (not “it ran”). 1 retry = 2 attempts on the same step. If that is not enough, or eval says the **plan** is wrong, 1 replan of the **remaining** suffix only; passed steps are not redone. Then `insufficient`. Typical plans: explain = search→retrieve→writer; compare = search×N→retrieve→writer; follow-up = retrieve→writer. Search does not load PDFs; retrieve hybrid 0.7/0.3 is under the hood. Caps: 1 retry/step, 1 replan/run, plus existing `max_steps` / timeout / `max_papers`.
**Reason:** User specified the loop; v1 combined researcher + retry-then-stop cannot drop a failed compare topic without either inventing coverage or failing the whole run.
**Trade-off:** Split roster (`search`/`retrieve` vs one `researcher`); stricter eval; one extra planner call per run at most.
**Impact:** Spec and design approved 2026-08-27. Supersedes ORCH-01, ORCH-02, CAP-01 retry count, combined `researcher` plan step, and THR-02 `reuse_existing_papers` mechanism. Gate, SSE event names, Writer grounding (ORCH-03), Chainlit unchanged. Consecutive `search` steps may `Send` in parallel; semantic search eval is **one** structured LLM call per wave with **N independent verdicts** (SEARCH-02).

### AD-012: Eval-replan design locks (2026-08-27)

**Decision:** Approve `.specs/features/orchestrator-eval-replan/design.md`. Search waves use LangGraph `Send` and admit papers only after eval pass. Hybrid retrieve is `EnsembleRetriever` RRF weights 0.7/0.3 (`langchain-classic` + BM25), not linear score fusion. Follow-up omits `search` (drop `reuse_existing_papers`). `Policy.max_retries_per_step=1`, `max_replans=1`. Mixed-wave remaining head is the earliest unpassed step; later passed searches are not rerun.
**Reason:** User approved the design as written.
**Trade-off:** RRF ≠ raw 0.7/0.3 score mix; extra graph nodes (`dispatch`, `search`, `replan`).
**Impact:** Tasks and implementation must follow that design. PROJECT.md caps updated. Parent spec banner marks superseded IDs.

---

## Active Blockers

### B-001: Host port 5432 occupied (`hackathon2026-postgres`)

**Discovered:** 2026-08-27
**Impact:** `docker compose up` for this project's pgvector cannot bind 5432.
**Workaround:** Temporary pgvector on 5433 for repo smoke. Stop the other container, or map compose to a free port, before API/Chainlit UAT.
**Resolution:** Free 5432 or change this project's published port.

---

## Lessons Learned

- `ChatOpenAI` validates `OPENAI_API_KEY` at construct time. Agent factory must pass `api_key` into Gate, Planner, and Writer runners; relying on env alone fails when Settings reads `.env` without exporting it.
- Parallel `[P]` tasks cannot each `git commit` safely; implement in parallel, then serialize atomic commits on the orchestrator.
- Sharing one psycopg pool with `AsyncPostgresSaver` (`dict_row`) means app SQL must read rows by column name (or set `tuple_row` on those cursors). Indexing `row[0]` crashes on cache hit and on RAG `fetchall`.
- On Windows, psycopg async cannot use the default `ProactorEventLoop`; smoke/scripts need `WindowsSelectorEventLoopPolicy` (uvicorn typically already uses a compatible loop).

---

## Quick Tasks Completed

| #   | Description | Date | Commit | Status |
| --- | ----------- | ---- | ------ | ------ |
| 001 | Install v1 stack (FastAPI, LangGraph, LangChain, OpenAI, Tavily) via uv | 2026-08-25 | — | ✅ Done |

---

## Deferred Ideas

- [ ] Automated test suite (pytest / Testcontainers) — Captured during: tasks phase (explicitly deferred)
- [ ] Writer `answer_delta` after eval pass — Captured during: grill-me
- [ ] Auth, multi-user, billing — Captured during: project init
- [ ] Thread TTL/delete and history UI across browser sessions — Captured during: grill-me
- [ ] arXiv TeX/HTML instead of PDF extract — Captured during: grill-me
- [ ] Dockerize API and Chainlit — Captured during: grill-me
- [ ] Global semantic search over full ingested corpus — Captured during: grill-me
- [ ] HITL plan approval — Captured during: grill-me
- [ ] Human-in-the-loop two-step plan confirm — Captured during: grill-me

---

## Todos

- [x] User approve `.specs/features/arxiv-grounded-research/spec.md` before Design
- [x] User approve `.specs/features/arxiv-grounded-research/design.md` before Tasks
- [x] Automated tests deferred (no pytest/Testcontainers in v1 tasks)
- [x] User approve `.specs/features/arxiv-grounded-research/tasks.md` before Execute
- [x] Remove Tavily from runtime dependencies when implementing Foundation
- [x] Fix: `PgChunkRepository` row mapping under `dict_row` (ARX-03 / EMB-01)
- [x] Fix: `CREATE TABLE` / `CREATE INDEX` `IF NOT EXISTS` on API restart (RUN-01)
- [x] Fix: researcher retry uses `last_eval.feedback`; `citations[]` only used `[n]`
- [ ] Manual UAT: in-domain SSE, out-of-domain gate, Chainlit `[n]` side panel, follow-up omit-search (needs free Postgres port)
- [x] User approve `.specs/features/orchestrator-eval-replan/spec.md`
- [x] User approve `.specs/features/orchestrator-eval-replan/design.md` before Tasks
- [x] After spec+design approval: update PROJECT.md caps (`max_retries_per_step` → 1 retry / 2 attempts; add `max_replans=1`) and parent spec superseded IDs
- [ ] User approve `.specs/features/orchestrator-eval-replan/tasks.md` before Execute

---

## Preferences

**Model Guidance Shown:** 2026-08-27 — validation / STATE / spec traceability is a good fit for a faster model.
