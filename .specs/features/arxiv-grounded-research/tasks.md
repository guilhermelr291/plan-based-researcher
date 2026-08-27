# ArXiv-Grounded Research Tasks

**Design**: `.specs/features/arxiv-grounded-research/design.md`  
**Status**: Draft (pending user approval)

Automated tests (pytest, Testcontainers, e2e) are **out of scope for this task list**. Done-when is implementation complete vs the design. Spec “Independent Test” lines stay as later manual checks, not as Execute work.

---

## Execution Plan

### Phase 1: Skeleton (T1 then parallel)

```
T1 ─┬─ T2 [P]
    ├─ T3 [P]
    ├─ T4 [P]
    ├─ T6 [P]
    ├─ T7 [P]
    ├─ T8 [P]
    ├─ T9 [P]
    ├─ T10 [P]
    └─ T11 [P]
```

### Phase 2: Policy, schemas, adapters

```
T3 ──→ T5
T7 ──→ T12
T8 ──→ T13 [P]
T10 ─→ T14 [P]
T12,T7 ──→ T31 [P]
```

### Phase 3: Adapters, repo, runners

```
T13 ──→ T15
T8,T9,T10 ──→ T16 [P]
T11 ─┬─ T17 [P]
     └─ T18 [P]
T11,T8,T9 ──→ T19
T11,T7 ──→ T20 [P]
T6,T3,T5 ──→ T22 [P]
T15,T17,T18,T19,T20 ──→ T21
```

### Phase 4: Graph then API

```
T21,T22 ─┬─ T23 [P]
         ├─ T24 [P]
         ├─ T25 [P]
         ├─ T26 [P]
         └─ T27 [P]
T23–T27 ──→ T28
T28,T12 ──→ T30 [P]
T28,T16 ──→ T29
```

---

## Task Breakdown

### T1: Package skeleton

**What**: Create `src/plan_based_researcher` package; add runtime deps from design; remove `langchain-tavily`.
**Where**: `pyproject.toml`, `src/plan_based_researcher/__init__.py`
**Depends on**: None
**Reuses**: existing `pyproject.toml`
**Requirement**: RUN-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Installable package layout (`src/plan_based_researcher`)
- [ ] Design add-deps listed; Tavily gone

**Commit**: `chore(research): bootstrap package`

---

### T2: Settings [P]

**What**: Typed `Settings` (`openai_api_key`, `database_url`, `api_host`, `api_port=8001`, `research_timeout_seconds=120`).
**Where**: `src/plan_based_researcher/config.py`
**Depends on**: T1
**Reuses**: pydantic-settings
**Requirement**: RUN-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Defaults match design; readable from env

**Commit**: `feat(research): add settings`

---

### T3: Policy [P]

**What**: `Policy` allowlist, caps, recency, splitter 500/100, `is_allowlisted`, `within_recency`.
**Where**: `src/plan_based_researcher/policy.py`
**Depends on**: T1
**Reuses**: spec constraint table
**Requirement**: GATE-02, ARX-02, CAP-01, EMB-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Categories exactly `cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`, `cs.NE`, `cs.RO`, `stat.ML`
- [ ] Caps 8 / 2 / 8; historical bypasses recency

**Commit**: `feat(research): add research policy`

---

### T4: Compose Postgres [P]

**What**: `docker-compose.yml` pgvector service + `.env.example`.
**Where**: `docker-compose.yml`, `.env.example`
**Depends on**: T1
**Reuses**: design RUN-01
**Requirement**: RUN-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Image `pgvector/pgvector` (pg16 or documented tag), port 5432, volume
- [ ] `.env.example` has `DATABASE_URL`, `OPENAI_API_KEY`, `API_PORT=8001`

**Commit**: `chore(research): add pgvector compose`

---

### T5: Graph state reducers

**What**: `GraphState` TypedDict, `merge_papers` reducer (unique `(arxiv_id, version)`, trim `max_papers`).
**Where**: `src/plan_based_researcher/graph/state.py`
**Depends on**: T3
**Reuses**: LangGraph `add_messages`
**Requirement**: THR-01, ARX-04

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] Duplicate keys merge; excess unique papers trimmed to `Policy.max_papers`

**Commit**: `feat(research): add graph state`

---

### T6: EvalResult [P]

**What**: `EvalResult` `{ status: pass|retry|fail, feedback }` — not exceptions.
**Where**: `src/plan_based_researcher/eval/types.py`
**Depends on**: T1
**Reuses**: design PAT-05
**Requirement**: ORCH-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Only those three statuses exist on the type

**Commit**: `feat(research): add eval result type`

---

### T7: HTTP schemas [P]

**What**: `ResearchRequest`, `Citation`, `AnswerCompleteData`, `GateDecision`, `PlanStep`, `ResearchPlan`.
**Where**: `src/plan_based_researcher/api/schemas.py`
**Depends on**: T1
**Reuses**: Pydantic
**Requirement**: API-01, GROUND-02, PLAN-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Empty `thread_id` fails validation
- [ ] `ResearchPlan.reuse_existing_papers` defaults False

**Commit**: `feat(research): add API schemas`

---

### T8: Paper port [P]

**What**: `PaperHit` + `PaperPort` protocol (`search`, `load_pdf_text`).
**Where**: `src/plan_based_researcher/ports/papers.py`
**Depends on**: T1
**Reuses**: design ports
**Requirement**: ARX-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] `PaperHit` fields match design

**Commit**: `feat(research): add paper port`

---

### T9: Chunks port [P]

**What**: `ChunkRepository` protocol (`get_paper`, `upsert_paper_with_chunks`, `similarity_search`).
**Where**: `src/plan_based_researcher/ports/chunks.py`
**Depends on**: T1
**Reuses**: design PAT-09
**Requirement**: ARX-03

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Protocol methods match design signatures

**Commit**: `feat(research): add chunk repository protocol`

---

### T10: Embeddings port [P]

**What**: `EmbeddingPort` protocol `embed_documents` / `embed_query`.
**Where**: `src/plan_based_researcher/ports/embeddings.py`
**Depends on**: T1
**Reuses**: design embedding port
**Requirement**: EMB-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Protocol matches design

**Commit**: `feat(research): add embedding port`

---

### T11: Agent registry [P]

**What**: `REGISTRY` for `gate|planner|researcher|writer` + `planner_prompt_abilities()`.
**Where**: `src/plan_based_researcher/agents/registry.py`
**Depends on**: T1
**Reuses**: design PAT-02
**Requirement**: PLAN-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Planner prompt includes all four agent names
- [ ] Models: planner/writer `gpt-5.1`, others `gpt-5-mini`

**Commit**: `feat(research): add agent registry`

---

### T12: SSE mapper

**What**: Encode `{event, data}` to `event:`/`data:` frames; allowlist spec names; never emit `answer_delta`.
**Where**: `src/plan_based_researcher/api/sse.py`
**Depends on**: T7
**Reuses**: PAT-11
**Requirement**: SSE-01, SSE-02, CAP-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Spec event names only; `answer_delta` not in the allowlist/helpers

**Commit**: `feat(research): add SSE frame mapper`

---

### T13: ArXiv adapter [P]

**What**: `ArxivPaperAdapter` implementing `PaperPort`; LangChain arXiv only inside adapter; sync I/O via `asyncio.to_thread`.
**Where**: `src/plan_based_researcher/adapters/arxiv.py`
**Depends on**: T8
**Reuses**: `ArxivRetriever`/`ArxivQueryRun`, `ArxivLoader`
**Requirement**: ARX-01, RUN-01

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] Search/load go through `to_thread` for sync clients
- [ ] No other search vendor imported

**Commit**: `feat(research): add arXiv adapter`

---

### T14: OpenAI embeddings adapter [P]

**What**: `OpenAIEmbeddingAdapter` for `text-embedding-3-small`.
**Where**: `src/plan_based_researcher/adapters/openai_embeddings.py`
**Depends on**: T10
**Reuses**: `langchain_openai.OpenAIEmbeddings`
**Requirement**: EMB-01

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] Model id is `text-embedding-3-small`

**Commit**: `feat(research): add embeddings adapter`

---

### T15: Tool registry

**What**: `ToolRegistry.get("arxiv_search"|"arxiv_load")` from `PaperPort`.
**Where**: `src/plan_based_researcher/agents/tools.py`
**Depends on**: T13
**Reuses**: PAT-03
**Requirement**: ARX-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Lookup by name; unknown name raises

**Commit**: `feat(research): add tool registry`

---

### T16: Chunk repository [P]

**What**: SQL `papers`/`chunks`, `get_paper` hit/miss, upsert, similarity search **IN** selected keys only.
**Where**: `src/plan_based_researcher/repo/chunks.py`
**Depends on**: T8, T9, T10
**Reuses**: psycopg + pgvector
**Requirement**: ARX-03, ARX-04

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Schema matches design (`vector` extension, PK `(arxiv_id, version)`)
- [ ] RAG query filters to provided paper keys (not full-library k-NN)

**Commit**: `feat(research): add pgvector chunk repository`

---

### T17: Gate runner [P]

**What**: Gate agent structured `GateDecision`; does not call arXiv.
**Where**: `src/plan_based_researcher/agents/gate.py`
**Depends on**: T11
**Reuses**: `with_structured_output`
**Requirement**: GATE-01, GATE-02

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] Structured `in_domain` / `language` / `reason`
- [ ] No `PaperPort` usage in this module

**Commit**: `feat(research): add gate runner`

---

### T18: Planner runner [P]

**What**: Planner returns `ResearchPlan`; validates `agent` ∈ REGISTRY; `reuse_existing_papers` for follow-up.
**Where**: `src/plan_based_researcher/agents/planner.py`
**Depends on**: T11
**Reuses**: registry abilities in prompt
**Requirement**: PLAN-01, THR-02

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] Invalid agent name rejected after parse
- [ ] `historical` and `reuse_existing_papers` on the plan type

**Commit**: `feat(research): add planner runner`

---

### T19: Researcher runner

**What**: Search → filter policy → load/upsert via repo → retrieve chunks → assign `[n]`. Honors `reuse_existing_papers` (no search).
**Where**: `src/plan_based_researcher/agents/researcher.py`
**Depends on**: T11, T8, T9
**Reuses**: PaperPort + ChunkRepository
**Requirement**: ARX-01, ARX-02, ARX-03, ARX-04, EMB-01, GROUND-01, THR-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Allowlist + recency (unless historical); `max_papers` cap
- [ ] Reuse path skips `search`
- [ ] Chunks numbered `[1…]` for the Writer

**Commit**: `feat(research): add researcher runner`

---

### T20: Writer runner [P]

**What**: Writer markdown + `citations[]` from numbered chunks; contradiction section in the prompt.
**Where**: `src/plan_based_researcher/agents/writer.py`
**Depends on**: T11, T7
**Reuses**: ChatOpenAI `gpt-5.1`
**Requirement**: GROUND-01, GROUND-02, GROUND-03

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Prompt includes formatted `[n]` blocks
- [ ] Prompt forbids citing indices not in the list and requires stating conflicts

**Commit**: `feat(research): add writer runner`

---

### T21: Agent factory

**What**: `AgentFactory.create(name)` returns runner; lookup table, not `if/elif` in the orchestrator.
**Where**: `src/plan_based_researcher/agents/factory.py`
**Depends on**: T15, T17, T18, T19, T20
**Reuses**: PAT-02
**Requirement**: PLAN-01, ORCH-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] All four v1 names resolve; unknown name raises

**Commit**: `feat(research): add agent factory`

---

### T22: Eval strategies [P]

**What**: `ResearchEvalStrategy` and `WriterEvalStrategy`; checklists from Policy (one copy of the rules).
**Where**: `src/plan_based_researcher/eval/strategies.py`
**Depends on**: T6, T3, T5
**Reuses**: PAT-05
**Requirement**: ORCH-02, ORCH-03

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Research eval uses allowlist/date/coverage rules from Policy
- [ ] Writer eval requires real `[n]`, query language, student tone, no extra sources

**Commit**: `feat(research): add eval strategies`

---

### T23: Gate node [P]

**What**: Graph node `gate` emits custom event `gate`; `outcome=refused` when out of domain.
**Where**: `src/plan_based_researcher/graph/nodes/gate.py`
**Depends on**: T21
**Reuses**: `StreamWriter` / `get_stream_writer`
**Requirement**: GATE-01, GATE-02

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] Event name `gate`; refuse sets `outcome`

**Commit**: `feat(research): add gate graph node`

---

### T24: Planner node [P]

**What**: Node `planner` emits `plan`; stores steps on state.
**Where**: `src/plan_based_researcher/graph/nodes/planner.py`
**Depends on**: T21
**Reuses**: planner runner
**Requirement**: PLAN-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] `state["plan"]` filled; event `plan`

**Commit**: `feat(research): add planner graph node`

---

### T25: Execute node [P]

**What**: Node `execute` looks up `plan[step_index].agent` via factory; emits `step_start`/`step_end` (hit/miss).
**Where**: `src/plan_based_researcher/graph/nodes/execute.py`
**Depends on**: T21
**Reuses**: PAT-04
**Requirement**: ORCH-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Dispatch by registry name only
- [ ] Events `step_start` and `step_end`

**Commit**: `feat(research): add execute graph node`

---

### T26: Evaluate node [P]

**What**: Node `evaluate` picks strategy by `last_agent`; increments retries; emits `eval`.
**Where**: `src/plan_based_researcher/graph/nodes/evaluate.py`
**Depends on**: T21, T22
**Reuses**: EvalResult
**Requirement**: ORCH-01, ORCH-02, ORCH-03, CAP-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] retry vs advance vs fail on state
- [ ] `max_retries_per_step` applied

**Commit**: `feat(research): add evaluate graph node`

---

### T27: Finalize node [P]

**What**: Node `finalize` emits `answer_complete` only on writer pass; else `done` / `insufficient` / `error`.
**Where**: `src/plan_based_researcher/graph/nodes/finalize.py`
**Depends on**: T21, T12
**Reuses**: SSE event names
**Requirement**: SSE-02, GROUND-02, CAP-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] No `answer_complete` on refuse/insufficient
- [ ] Pass path includes markdown + citations

**Commit**: `feat(research): add finalize graph node`

---

### T28: Compile graph

**What**: `build_graph` + conditional edges (gate → planner|finalize, execute ↔ evaluate, caps → finalize).
**Where**: `src/plan_based_researcher/graph/build.py`
**Depends on**: T23, T24, T25, T26, T27
**Reuses**: LangGraph `START`/`END`
**Requirement**: ORCH-01, THR-01, THR-02, GATE-01

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] Compiled graph matches design state diagram
- [ ] `reuse_existing_papers` is visible to the researcher via state/plan

**Commit**: `feat(research): compile research state graph`

---

### T30: Research HTTP route [P]

**What**: `POST /research` SSE; HTTP 400 without `thread_id`; `iter_sse` + `asyncio.wait_for`.
**Where**: `src/plan_based_researcher/api/routes.py`, `src/plan_based_researcher/api/deps.py`
**Depends on**: T28, T12
**Reuses**: FastAPI `StreamingResponse`
**Requirement**: API-01, SSE-01, SSE-02, CAP-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [ ] Missing/blank `thread_id` → 400, graph not started
- [ ] Success path `Content-Type: text/event-stream`
- [ ] Timeout yields `insufficient` or `error` then closes

**Commit**: `feat(research): add POST /research SSE`

---

### T31: Chainlit mapper [P]

**What**: SSE→Chainlit mapping (`cl.Step`, side-panel `[n]`); `ui/app.py` HTTP client only (no graph import).
**Where**: `src/plan_based_researcher/ui/sse_map.py`, `src/plan_based_researcher/ui/app.py`
**Depends on**: T12, T7
**Reuses**: UI-01–03
**Requirement**: UI-01, UI-02, UI-03

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] `app.py` does not import `plan_based_researcher.graph`
- [ ] New chat creates `thread_id` in session; messages POST `{ query, thread_id }`
- [ ] `[n]` mapped to `cl.Text(..., display="side")`

**Commit**: `feat(research): add Chainlit SSE mapping`

---

### T29: Lifespan and health

**What**: FastAPI lifespan: pool, `AsyncPostgresSaver.setup()`, app schema, `GET /health`.
**Where**: `src/plan_based_researcher/main.py`
**Depends on**: T28, T16
**Reuses**: PAT-07, PAT-12
**Requirement**: THR-01, RUN-01

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [ ] Graph compiled once at startup with `AsyncPostgresSaver(pool)`
- [ ] `GET /health` pings Postgres
- [ ] App `papers`/`chunks` schema created on startup (or documented migration equivalent)

**Commit**: `feat(research): add API lifespan and health`

---

## Parallel Execution Map

```
Phase 1:
  T1 → { T2, T3, T4, T6, T7, T8, T9, T10, T11 } [P]

Phase 2:
  T3 → T5
  T7 → T12
  T8 → T13 [P]
  T10 → T14 [P]
  T12+T7 → T31 [P]

Phase 3:
  T13 → T15
  T8+T9+T10 → T16 [P]
  T11 → T17 [P], T18 [P]
  T11+T8+T9 → T19
  T11+T7 → T20 [P]
  T6+T3+T5 → T22 [P]
  T15+T17+T18+T19+T20 → T21

Phase 4:
  T21+T22 → { T23, T24, T25, T26, T27 } [P]
  T23–T27 → T28
  T28+T12 → T30 [P]
  T28+T16 → T29
```

T31 may start as soon as T12 and T7 are done.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1 | package + deps | ✅ |
| T2–T3, T5–T15, T17–T27 | one module | ✅ |
| T4 | compose + env | ✅ cohesive |
| T16 | chunk repo | ✅ |
| T28 | build_graph | ✅ |
| T30 | routes + deps | ✅ cohesive |
| T31 | sse_map + app | ✅ cohesive |
| T29 | main lifespan | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
| ---- | ----------------- | ------------- | ------ |
| T1 | None | source | ✅ |
| T2 | T1 | T1 → T2 | ✅ |
| T3 | T1 | T1 → T3 | ✅ |
| T4 | T1 | T1 → T4 | ✅ |
| T5 | T3 | T3 → T5 | ✅ |
| T6 | T1 | T1 → T6 | ✅ |
| T7 | T1 | T1 → T7 | ✅ |
| T8 | T1 | T1 → T8 | ✅ |
| T9 | T1 | T1 → T9 | ✅ |
| T10 | T1 | T1 → T10 | ✅ |
| T11 | T1 | T1 → T11 | ✅ |
| T12 | T7 | T7 → T12 | ✅ |
| T13 | T8 | T8 → T13 | ✅ |
| T14 | T10 | T10 → T14 | ✅ |
| T15 | T13 | T13 → T15 | ✅ |
| T16 | T8, T9, T10 | T8+T9+T10 → T16 | ✅ |
| T17 | T11 | T11 → T17 | ✅ |
| T18 | T11 | T11 → T18 | ✅ |
| T19 | T11, T8, T9 | T11+T8+T9 → T19 | ✅ |
| T20 | T11, T7 | T11+T7 → T20 | ✅ |
| T21 | T15, T17, T18, T19, T20 | those → T21 | ✅ |
| T22 | T6, T3, T5 | T6+T3+T5 → T22 | ✅ |
| T23 | T21 | T21 → T23 | ✅ |
| T24 | T21 | T21 → T24 | ✅ |
| T25 | T21 | T21 → T25 | ✅ |
| T26 | T21, T22 | T21+T22 → T26 | ✅ |
| T27 | T21, T12 | T21+T12 → T27 | ✅ |
| T28 | T23–T27 | T23–T27 → T28 | ✅ |
| T30 | T28, T12 | T28+T12 → T30 | ✅ |
| T31 | T12, T7 | T12+T7 → T31 | ✅ |
| T29 | T28, T16 | T28+T16 → T29 | ✅ |

T12 completes in Phase 2 before T27. ✅

---

## Requirement coverage

| ID | Tasks |
| -- | ----- |
| API-01 | T7, T30 |
| SSE-01 | T12, T30 |
| SSE-02 | T12, T27, T30 |
| GATE-01 | T17, T23, T28 |
| GATE-02 | T3, T17, T23 |
| PLAN-01 | T7, T11, T18, T21, T24 |
| ORCH-01 | T6, T21, T25, T26, T28 |
| ORCH-02 | T22, T26 |
| ORCH-03 | T22, T26 |
| ARX-01 | T8, T13, T15, T19 |
| ARX-02 | T3, T19 |
| ARX-03 | T9, T16, T19 |
| ARX-04 | T5, T16, T19 |
| EMB-01 | T3, T10, T14, T19 |
| GROUND-01 | T19, T20 |
| GROUND-02 | T7, T20, T27 |
| GROUND-03 | T20 |
| CAP-01 | T3, T12, T26, T27, T30 |
| THR-01 | T5, T28, T29 |
| THR-02 | T18, T19, T28 |
| UI-01 | T31 |
| UI-02 | T31 |
| UI-03 | T31 |
| RUN-01 | T1, T2, T4, T13, T29 |

**Coverage:** 24/24 mapped.
