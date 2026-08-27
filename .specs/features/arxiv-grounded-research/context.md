# ArXiv-Grounded Research — Architecture Constraints

**Gathered:** 2026-08-26  
**Spec:** `.specs/features/arxiv-grounded-research/spec.md`  
**Status:** Locked from chat (design-pattern discussion)

These are implementation constraints for Design/Tasks. They do not change product behavior in the spec; they constrain *how* the graph, agents, and HTTP edge are structured.

---

## Feature boundary (unchanged)

SSE via FastAPI `StreamingResponse`, Chainlit as HTTP client, LangGraph as the only orchestrator, arXiv + pgvector outbound I/O.

---

## Locked decisions

### PAT-01 — LangGraph is the orchestrator

Do not add a second routing engine, supervisor-chat, mediator bus, or workflow product on top of `StateGraph`. The plan-based loop is graph state (`plan`, `step_index`, retries) plus conditional edges.

### PAT-02 — Agent registry + factory

- **Registry:** single source of agent names and abilities. The Planner prompt is built from this map. The Orchestrator dispatches `step.agent` via lookup, not `if/elif` on agent names.
- **Factory:** given a registry name, bind model (`gpt-5.1` vs `gpt-5-mini`), tools, and structured-output schema.
- Adding a specialist later = new registry entry + abilities text, not a new edge soup.

### PAT-03 — Tool registry (Researcher)

ArXiv search and PDF load (`ArxivRetriever` / `ArxivQueryRun`, `ArxivLoader`) are obtained from a tool registry/adapter, not constructed ad hoc inside multiple graph nodes.

### PAT-04 — Plan interpreter

The Planner emits structured steps `{ agent, task, reasoning }`. The Orchestrator **interprets** that list (execute → eval → retry or advance). Do not use a free-form LLM supervisor to pick nodes.

### PAT-05 — Eval strategies + result type

- Researcher eval and Writer grounding eval share an interface and differ by checklist (Strategy).
- Business outcomes are a result object `{ status: pass | retry | fail, feedback }` — not exceptions. Exceptions are for infrastructure failure only.

### PAT-06 — Typed graph state + reducers

Graph `State` is the source of truth (query, plan, papers, chunks, messages, cap counters). Use reducers so nodes do not clobber each other. `AsyncPostgresSaver` persists this state by `thread_id`.

### PAT-07 — Compile once (lifespan)

Compile the graph once in the FastAPI lifespan with `AsyncPostgresSaver` (and `setup()`). Each `POST /research` only passes `thread_id` in config. Do not rebuild `StateGraph` per request.

### PAT-08 — Outbound ports only (no HTTP/UI adapter classes)

Isolate **outbound** I/O behind ports/adapters:

- Paper search / PDF load (LangChain arXiv)
- Chunk store (pgvector)
- Optional: embeddings if not already behind the factory

**Do not** create `FastAPIAdapter` or `ChainlitAdapter` wrappers. FastAPI routers *are* the HTTP edge. Chainlit is a client of `POST /research` and must not import the graph (already **UI-03**).

### PAT-09 — Chunk repository

`get(arxiv_id, version)` on hit skips PDF download; miss loads, splits (500/100), embeds, upserts. RAG remains restricted to papers selected for the current thread/query (not library-wide k-NN).

### PAT-10 — Policy objects

Category allowlist, caps (8 / 2 / 8, ~2 min), 5-year recency, splitter settings, and the grounding rule (“every technical claim has a real `[n]`”) live as named config/pure functions. Prompt text and eval checklists must not drift into two different copies of the same rule.

### PAT-11 — SSE is FastAPI `StreamingResponse`

No SSE framework. An async generator yields `event:` / `data:` frames. A small mapper translates `graph.astream` updates into spec event names (`gate`, `plan`, `step_start`, `step_end`, `eval`, `answer_complete`, `done` | `insufficient` | `error`). No `answer_delta`. Chainlit consumes this HTTP stream.

### PAT-12 — Dependency injection at the edge

Lifespan holds the compiled graph and repositories. Route handlers receive them via FastAPI `Depends`. Pydantic models stay at the HTTP boundary; graph state stays TypedDict/dataclasses.

---

## Explicitly out (do not build in v1)

- Abstract Factory of factories, plugin entry points, CQRS, per-agent microservices, global service locator
- Decorator-retries around LLM calls that duplicate Orchestrator retries
- Chainlit callbacks or LangGraph imports inside the UI process
- Wrapping FastAPI or Chainlit in hexagonal “adapter” classes

---

## Suggested module split (non-normative until Design)

| Area | Pattern |
| ---- | ------- |
| `agents/registry.py` | PAT-02 |
| `agents/factory.py` | PAT-02 |
| `graph/state.py` | PAT-06 |
| `graph/orchestrator.py` | PAT-04, PAT-01 |
| `eval/strategies.py` | PAT-05 |
| `ports/` + `adapters/arxiv.py` | PAT-03, PAT-08 |
| `repo/chunks.py` | PAT-09 |
| `api/sse.py` | PAT-11 |
| FastAPI lifespan | PAT-07, PAT-12 |
