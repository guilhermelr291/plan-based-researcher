# Orchestrator Eval and Remaining-Plan Replan Tasks

**Design**: `.specs/features/orchestrator-eval-replan/design.md`  
**Status**: Validation 2026-08-27 (uncommitted). T1–T24 implemented; LOOP-02 per-step `eval_by_step` and always-formulate search/retrieve queries added 2026-08-28.

Automated tests (pytest, Testcontainers, e2e) are **out of scope**, same as v1. There is no `.specs/codebase/TESTING.md`. Done-when is implementation complete vs the approved design. Spec “Independent Test” lines stay as later manual UAT, not Execute work.

---

## Execution Plan

### Phase 1: Types and policy (all `[P]`)

```
T1 [P]  T2 [P]  T3 [P]  T4 [P]  T5 [P]  T6 [P]  T7 [P]
```

### Phase 2: Runners and eval (after Phase 1)

```
T6 ──→ T8 ──→ T9 ──→ T11 ──┐
T5,T7 ──→ T10 [P] ─────────┴──→ T14
T4,T7 ──→ T12 [P]
T2,T3,T5 ──→ T13 [P]
T2,T5 ──→ T15 [P]
T4 ──→ T21 [P]
```

### Phase 3: Graph nodes (after their deps)

```
T14 ─┬─ T16 [P]
     └─ T17 [P]
T13 ─── T18 [P]
T12 ─┬─ T19 [P]
     └─ T20 [P]
```

### Phase 4: Wire and cleanup

```
T14,T15,T16,T17,T18,T19,T20 ──→ T22 ──→ T23
T11,T14 ──→ T24 [P]
```

T24 may run in parallel with T22 (not with T23).

---

## Task Breakdown

### T1: Hybrid retrieve dependencies [P]

**What**: Add direct deps `langchain-classic` and `rank-bm25` (EnsembleRetriever + BM25).
**Where**: `pyproject.toml`
**Depends on**: None
**Reuses**: existing `uv` lock workflow
**Requirement**: RETR-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Both packages listed under `[project].dependencies`
- [x] Lockfile updated (`uv lock` / `uv sync`)

**Tests**: none
**Gate**: none

**Verify**: `uv sync` succeeds; `python -c "from langchain_classic.retrievers import EnsembleRetriever"`

**Commit**: `chore(eval-replan): add ensemble and bm25 deps`

---

### T2: Policy caps and hybrid weights [P]

**What**: Set `max_retries_per_step=1`, add `max_replans=1`, hybrid 0.7/0.3, `retrieve_k=8`.
**Where**: `src/plan_based_researcher/policy.py`
**Depends on**: None
**Reuses**: existing `Policy` class
**Requirement**: CAP-02, RETR-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `max_retries_per_step == 1` (2 attempts with existing `count > cap` logic)
- [x] `max_replans == 1`
- [x] `hybrid_vector_weight == 0.7`, `hybrid_lexical_weight == 0.3`, `retrieve_k == 8`
- [x] `max_steps` / `max_papers` / splitter unchanged

**Tests**: none
**Gate**: none

**Verify**: Read `Policy` class; caps match design.

**Commit**: `feat(eval-replan): update policy caps and hybrid weights`

---

### T3: Eval result types [P]

**What**: Add `plan_inadequate` on `EvalResult`; add `SearchStepVerdict` and `SearchWaveJudgement`.
**Where**: `src/plan_based_researcher/eval/types.py`
**Depends on**: None
**Reuses**: existing `EvalResult`
**Requirement**: LOOP-02, LOOP-03, SEARCH-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `EvalResult.status` still `pass|retry|fail`; `plan_inadequate: bool = False`
- [x] Wave types match design (`step_index`, `passed`, `plan_inadequate`, `feedback`, `verdicts`, `reasoning`)

**Tests**: none
**Gate**: none

**Verify**: Import the three models from `eval.types`.

**Commit**: `feat(eval-replan): extend eval result types`

---

### T4: Drop reuse_existing_papers from plan schema [P]

**What**: Remove `ResearchPlan.reuse_existing_papers`; keep `{ agent, task, reasoning, historical }`.
**Where**: `src/plan_based_researcher/api/schemas.py`
**Depends on**: None
**Reuses**: existing `PlanStep`
**Requirement**: PLAN-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `ResearchPlan` has `steps` only (no reuse flag)

**Tests**: none
**Gate**: none

**Verify**: `ResearchPlan.model_fields` has no `reuse_existing_papers`.

**Commit**: `feat(eval-replan): drop reuse_existing_papers from plan schema`

---

### T5: Graph state for waves, retries, replan [P]

**What**: Add `passed_steps`, `retry_counts`, `replan_used`, `search_artifacts` + `merge_search_artifacts`; keep `merge_papers` for admitted papers only.
**Where**: `src/plan_based_researcher/graph/state.py`
**Depends on**: None
**Reuses**: existing `GraphState`, `PaperRef`, `merge_papers`
**Requirement**: LOOP-01, SEARCH-01, REPLAN-01, CAP-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `SearchHit` / `SearchArtifact` TypedDicts match design
- [x] `search_artifacts` uses last-write-wins dict merge (not `operator.add` on a list)
- [x] `retry_counts` keys are JSON-safe strings
- [x] `steps_executed` stays a plain int (no parallel add reducer)
- [x] Nodes can `.get()`-default new keys for old checkpoints

**Tests**: none
**Gate**: none

**Verify**: `GraphState` annotations match design data models.

**Commit**: `feat(eval-replan): extend graph state for wave and replan`

---

### T6: list_chunks port [P]

**What**: Add `ChunkRepository.list_chunks(paper_keys) -> list[EvidenceChunk]`.
**Where**: `src/plan_based_researcher/ports/chunks.py`
**Depends on**: None
**Reuses**: existing `EvidenceChunk`
**Requirement**: RETR-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Protocol includes `list_chunks` with the design signature

**Tests**: none
**Gate**: none

**Verify**: Protocol has three prior methods plus `list_chunks`.

**Commit**: `feat(eval-replan): add list_chunks to chunk port`

---

### T7: Registry plan agents [P]

**What**: Replace `researcher` with `search` + `retrieve`; `PLAN_AGENTS`; planner prompt lists only those three.
**Where**: `src/plan_based_researcher/agents/registry.py`
**Depends on**: None
**Reuses**: existing `AgentSpec` / `REGISTRY` pattern
**Requirement**: PLAN-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `Role` includes `search` and `retrieve`, not `researcher`
- [x] `PLAN_AGENTS == frozenset({"search", "retrieve", "writer"})`
- [x] `planner_prompt_abilities()` emits only `PLAN_AGENTS`
- [x] `search` tools `("arxiv_search",)`; `retrieve` tools `("arxiv_load",)`; both `gpt-5-mini`
- [x] `writer` / `gate` / `planner` unchanged besides planner abilities text (no reuse flag)

**Tests**: none
**Gate**: none

**Verify**: `"researcher" not in REGISTRY`; `"search"` and `"retrieve"` in `REGISTRY`.

**Commit**: `feat(eval-replan): split registry into search and retrieve`

---

### T8: list_chunks SQL

**What**: Implement `PgChunkRepository.list_chunks` filtered to `(arxiv_id, version)`, `dict_row` column names.
**Where**: `src/plan_based_researcher/repo/chunks.py`
**Depends on**: T6
**Reuses**: `similarity_search` join + unnest pattern
**Requirement**: RETR-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Empty `paper_keys` returns `[]`
- [x] Rows mapped by column name (not `row[0]`)
- [x] Ordered by `arxiv_id, version, chunk_index`

**Tests**: none
**Gate**: none

**Verify**: Method exists; SQL uses `unnest` IN-filter like similarity search.

**Commit**: `feat(eval-replan): list chunks for bm25 corpus`

---

### T9: Ensemble hybrid adapter

**What**: `HybridRetrievePort.retrieve` via `EnsembleRetriever` vector 0.7 + BM25 0.3, `id_key="chunk_id"`, admitted papers only.
**Where**: `src/plan_based_researcher/adapters/hybrid.py`
**Depends on**: T1, T2, T8
**Reuses**: `ChunkRepository.similarity_search` + `list_chunks`; PAT-08 (no `Document` in graph nodes)
**Requirement**: RETR-01

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [x] Empty `paper_keys` returns `[]` without building retrievers
- [x] Weights from `Policy`; `ainvoke`; map back to `EvidenceChunk`
- [x] LangChain types stay in this adapter

**Tests**: none
**Gate**: none

**Verify**: File imports `EnsembleRetriever` from `langchain_classic` and `BM25Retriever` from `langchain_community`.

**Commit**: `feat(eval-replan): add ensemble hybrid retriever adapter`

---

### T10: Search runner [P]

**What**: `SearchRunner` searches arXiv for this step’s task; allowlist/recency; no PDF; no write to `papers`; always formulate arXiv query via mini structured output.
**Where**: `src/plan_based_researcher/agents/search.py`
**Depends on**: T5, T7
**Reuses**: filter helpers in `agents/researcher.py`; `PaperPort.search`
**Requirement**: SEARCH-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Returns `search_artifacts: {str(step_index): SearchArtifact}` only (not `papers`)
- [x] Every attempt formulates arXiv query via `gpt-5-mini` structured output from task (+ that step’s feedback on retry)
- [x] Hits include title + abstract; no `load_pdf_text`

**Tests**: none
**Gate**: none

**Verify**: Module has no `load_pdf_text` / splitter / embed calls.

**Commit**: `feat(eval-replan): add search runner`

---

### T11: Retrieve runner

**What**: Move ingest from researcher into `RetrieveRunner`; hybrid retrieve; English query formulated on every attempt; number `[n]`.
**Where**: `src/plan_based_researcher/agents/retrieve.py`
**Depends on**: T5, T7, T9
**Reuses**: ingest loop from `agents/researcher.py`
**Requirement**: RETR-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Uses `state["papers"]` only (admitted); no arXiv search
- [x] Cache miss → PDF → split 500/100 → embed → upsert
- [x] Hybrid `Policy.retrieve_k`; `pgvector` hit/miss; `last_agent: "retrieve"`
- [x] Retry rewrite is English; same paper set
- [x] Every attempt formulates an English hybrid query via structured output from the task

**Tests**: none
**Gate**: none

**Verify**: No `PaperPort.search` in this file.

**Commit**: `feat(eval-replan): add retrieve runner`

---

### T12: Planner remaining-only path [P]

**What**: Prompt typical plan shapes; validate `PLAN_AGENTS`; add `replan_remaining` (suffix only); stop using `reuse_existing_papers`.
**Where**: `src/plan_based_researcher/agents/planner.py`
**Depends on**: T4, T7
**Reuses**: existing structured `ResearchPlan` + `planner_prompt_abilities()`
**Requirement**: PLAN-02, REPLAN-01, REPLAN-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Initial prompt: explain / compare `search`×N / follow-up omit `search`
- [x] Invalid agent raises
- [x] `replan_remaining` input includes prefix summary, admitted papers, failed step + feedback, leftover steps
- [x] Replan output is suffix steps only; REPLAN-02 example in prompt (evidenced vs missing topics)

**Tests**: none
**Gate**: none

**Verify**: No `reuse_existing_papers` in planner module.

**Commit**: `feat(eval-replan): planner shapes and remaining replan`

---

### T13: Search, retrieve, writer eval strategies [P]

**What**: Replace `ResearchEvalStrategy` with `SearchEvalStrategy.evaluate_wave` (one LLM, N verdicts) + `RetrieveEvalStrategy`; keep Writer ORCH-03 and allow `plan_inadequate`.
**Where**: `src/plan_based_researcher/eval/strategies.py`
**Depends on**: T2, T3, T5
**Reuses**: existing writer deterministic `[n]` checks
**Requirement**: SEARCH-02, RETR-01, WRITE-01, LOOP-02, LOOP-03

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Wave eval: one structured `SearchWaveJudgement` call over artifacts in the wave (retry subset on retry)
- [x] Deterministic empty/allowlist/recency still feed that **one** call
- [x] Retrieve eval: chunks from admitted papers + semantic vs retrieve `task`
- [x] Writer eval unchanged grounding; retry uses same evidence (no new retrieve)

**Tests**: none
**Gate**: none

**Verify**: `ResearchEvalStrategy` is gone; `evaluate_wave` exists.

**Commit**: `feat(eval-replan): semantic search and retrieve eval`

---

### T14: Factory dispatch search and retrieve

**What**: Factory maps `search` / `retrieve` / `writer` / `gate` / `planner`; drop `researcher`.
**Where**: `src/plan_based_researcher/agents/factory.py`
**Depends on**: T7, T10, T11
**Reuses**: existing lookup-table factory
**Requirement**: PLAN-02, LOOP-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `create("search")` / `create("retrieve")` work; `create("researcher")` raises
- [x] Still no `if/elif` on names in graph nodes

**Tests**: none
**Gate**: none

**Verify**: `"researcher" not in AgentFactory._runners` (or equivalent).

**Commit**: `feat(eval-replan): factory search and retrieve runners`

---

### T15: Dispatch node [P]

**What**: Interpreter: consecutive unpassed `search` → `Send`; else retrieve/writer → execute; caps / oversized wave → insufficient.
**Where**: `src/plan_based_researcher/graph/nodes/dispatch.py`
**Depends on**: T2, T5
**Reuses**: LangGraph `Command` + `Send`; `Policy.max_steps`
**Requirement**: LOOP-01, SEARCH-01, CAP-02

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [x] `search_wave_indices` takes consecutive unpassed searches from first unpassed index
- [x] Wave not started if `steps_executed + len(wave) > max_steps`
- [x] No supervisor LLM

**Tests**: none
**Gate**: none

**Verify**: File uses `Send` / `Command`; no ChatOpenAI.

**Commit**: `feat(eval-replan): add dispatch node`

---

### T16: Search worker node [P]

**What**: Thin node: `step_start` / run `search` / `step_end` with `paper_ids` and `pgvector: "n/a"`. Do not increment `steps_executed`.
**Where**: `src/plan_based_researcher/graph/nodes/search.py`
**Depends on**: T14
**Reuses**: execute.py SSE shape
**Requirement**: SEARCH-01, LOOP-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] SSE `step_end` does not imply PDF
- [x] Worker returns artifact merge only (no `steps_executed`)

**Tests**: none
**Gate**: none

**Verify**: No `steps_executed` in the return dict.

**Commit**: `feat(eval-replan): add search worker node`

---

### T17: Execute retrieve and writer only [P]

**What**: Execute stays sequential for `retrieve` / `writer` via factory; unknown agent → `error`; still +1 `steps_executed`.
**Where**: `src/plan_based_researcher/graph/nodes/execute.py`
**Depends on**: T14
**Reuses**: existing execute node
**Requirement**: LOOP-01, WRITE-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Dispatches `plan[first_unpassed].agent` (not a hardcoded researcher)
- [x] Search is not executed here

**Tests**: none
**Gate**: none

**Verify**: Node still calls `factory.create(...).run`; increments `steps_executed` by 1.

**Commit**: `feat(eval-replan): execute retrieve and writer only`

---

### T18: Evaluate pass, retry, replan, admit [P]

**What**: Wave vs step eval; admit papers on search pass only; per-index retries; `plan_inadequate` skips leftover retry; N `eval` SSE frames for a wave; `steps_executed += len(wave)` after search join.
**Where**: `src/plan_based_researcher/graph/nodes/evaluate.py`
**Depends on**: T5, T13
**Reuses**: existing `eval` event; `Policy.max_retries_per_step`
**Requirement**: LOOP-01, LOOP-02, LOOP-03, SEARCH-01, SEARCH-02, CAP-02, WRITE-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Pass adds index to `passed_steps`; failed search does not merge into `papers`
- [x] Mixed wave: later passed searches stay passed; remaining head is earliest unpassed
- [x] Writer pass → `outcome=done`; no writer pass at end of plan → `insufficient`
- [x] Route to `dispatch` | `replan` | `finalize`

**Tests**: none
**Gate**: none

**Verify**: No `ResearchEvalStrategy` import; admits papers only on search pass.

**Commit**: `feat(eval-replan): evaluate wave retry and replan routing`

---

### T19: Replan remaining node [P]

**What**: Call planner suffix; concatenate prefix+suffix on state; SSE `plan` = suffix only; zero retries on new head; `replan_used=True`; empty / no writer → `insufficient`.
**Where**: `src/plan_based_researcher/graph/nodes/replan.py`
**Depends on**: T5, T12
**Reuses**: planner `plan` SSE payload shape
**Requirement**: REPLAN-01, REPLAN-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Passed prefix not re-executed; admitted papers kept
- [x] `step_index = len(prefix)`; new suffix retry counters 0
- [x] Existing `plan` event only (no new event name)

**Tests**: none
**Gate**: none

**Verify**: Writer event name is `plan`, not `replan`.

**Commit**: `feat(eval-replan): add remaining-plan replan node`

---

### T20: Planner node state init [P]

**What**: After initial plan, set `step_index=0`, `passed_steps=[]`, `retry_counts={}`, `replan_used=False`, `steps_executed=0`; emit `plan` with full steps (no reuse flag).
**Where**: `src/plan_based_researcher/graph/nodes/planner.py`
**Depends on**: T5, T12
**Reuses**: existing planner node SSE
**Requirement**: PLAN-02, LOOP-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `plan` SSE `data.steps` is the full initial list
- [x] No `reuse_existing_papers` in the event payload

**Tests**: none
**Gate**: none

**Verify**: Node `setdefault`s the new state keys.

**Commit**: `feat(eval-replan): init passed_steps and replan_used on plan`

---

### T21: Chainlit drop reuse banner [P]

**What**: Stop rendering `Reuse existing papers.` from `plan` events.
**Where**: `src/plan_based_researcher/ui/app.py`
**Depends on**: T4
**Reuses**: existing `_plan_text`
**Requirement**: PLAN-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `_plan_text` does not mention `reuse_existing_papers`
- [x] Still does not import `plan_based_researcher.graph`

**Tests**: none
**Gate**: none

**Verify**: Grep `reuse_existing_papers` is gone from `ui/app.py`.

**Commit**: `feat(eval-replan): drop reuse_existing_papers from chainlit plan text`

---

### T22: Compile dispatch–search–replan graph

**What**: `build_graph`: nodes `gate`, `planner`, `dispatch`, `search`, `execute`, `evaluate`, `replan`, `finalize`; `GraphDeps` uses new eval strategies.
**Where**: `src/plan_based_researcher/graph/build.py`
**Depends on**: T14, T15, T16, T17, T18, T19, T20
**Reuses**: compile-once + checkpointer (PAT-07)
**Requirement**: LOOP-01, LOOP-03, CAP-02

**Tools**: MCP context7 · Skill NONE

**Done when**:

- [x] Edges match design state diagram (`search` joins at `evaluate`; `evaluate` → dispatch | replan | finalize)
- [x] `ResearchEvalStrategy` not in `GraphDeps`

**Tests**: none
**Gate**: none

**Verify**: `build_graph` node names match the design list.

**Commit**: `feat(eval-replan): wire send-eval-replan graph`

---

### T23: Lifespan GraphDeps

**What**: FastAPI lifespan constructs search/retrieve/writer eval + factory with hybrid; compile graph once.
**Where**: `src/plan_based_researcher/main.py`
**Depends on**: T22
**Reuses**: existing pool / checkpointer / `AgentFactory` wiring
**Requirement**: LOOP-01, RETR-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] No `ResearchEvalStrategy` construct
- [x] Hybrid adapter (or retrieve runner) receives chunk repo + embeddings

**Tests**: none
**Gate**: none

**Verify**: App still `create_app()`; lifespan still `setup()` + `ensure_schema()`.

**Commit**: `feat(eval-replan): wire lifespan to split agents and eval`

---

### T24: Remove combined researcher runner [P]

**What**: Delete `agents/researcher.py` after factory no longer imports it.
**Where**: `src/plan_based_researcher/agents/researcher.py`
**Depends on**: T11, T14
**Reuses**: n/a (logic moved in T10/T11)
**Requirement**: PLAN-02, SEARCH-01, RETR-01

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] File removed; no remaining imports of `ResearcherRunner`

**Tests**: none
**Gate**: none

**Verify**: Repo-wide grep `ResearcherRunner` / `agents.researcher` is empty.

**Commit**: `refactor(eval-replan): remove combined researcher runner`

---

## Parallel Execution Map

```
Phase 1 (all [P]):
  T1 T2 T3 T4 T5 T6 T7

Phase 2:
  T8  → T9 → T11 ─┐
  T10 [P] ────────┴→ T14
  T12 [P]
  T13 [P]
  T15 [P]
  T21 [P]

Phase 3 (after listed deps):
  T16 [P] T17 [P]          ← T14
  T18 [P]                  ← T13
  T19 [P] T20 [P]          ← T12

Phase 4:
  T22 → T23
  T24 [P] with T22
```

**Parallelism constraint:** No `.specs/codebase/TESTING.md`. `[P]` is allowed from code dependencies only (v1 convention). Tasks in the same phase do not share a mutable file.

---

## Requirement traceability (tasks)

| ID | Tasks |
| -- | ----- |
| PLAN-02 | T4, T7, T12, T14, T20, T21, T24 |
| LOOP-01 | T5, T14, T15, T16, T17, T18, T20, T22, T23 |
| LOOP-02 | T3, T13, T18 |
| LOOP-03 | T3, T13, T18, T22 |
| SEARCH-01 | T5, T10, T15, T16, T18, T24 |
| SEARCH-02 | T3, T13, T18 |
| RETR-01 | T1, T2, T6, T8, T9, T11, T13, T23, T24 |
| WRITE-01 | T13, T17, T18 |
| REPLAN-01 | T5, T12, T19 |
| REPLAN-02 | T12, T19 |
| CAP-02 | T2, T5, T15, T18, T22 |

**Coverage:** 11/11 IDs mapped; no orphan tasks.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1 | 1 manifest (`pyproject.toml`) | ✅ Granular |
| T2 | 1 class file (`policy.py`) | ✅ Granular |
| T3 | 1 types module | ✅ Granular |
| T4 | 1 schema field removal | ✅ Granular |
| T5 | 1 state module | ✅ Granular |
| T6 | 1 protocol method | ✅ Granular |
| T7 | 1 registry module | ✅ Granular |
| T8 | 1 repo method | ✅ Granular |
| T9 | 1 adapter module | ✅ Granular |
| T10 | 1 runner module | ✅ Granular |
| T11 | 1 runner module | ✅ Granular |
| T12 | 1 planner module | ✅ Granular |
| T13 | 1 eval module (3 cohesive strategies) | ✅ Granular |
| T14 | 1 factory module | ✅ Granular |
| T15 | 1 graph node | ✅ Granular |
| T16 | 1 graph node | ✅ Granular |
| T17 | 1 graph node (modify) | ✅ Granular |
| T18 | 1 graph node (modify) | ✅ Granular |
| T19 | 1 graph node | ✅ Granular |
| T20 | 1 graph node (modify) | ✅ Granular |
| T21 | 1 UI helper | ✅ Granular |
| T22 | 1 graph builder | ✅ Granular |
| T23 | 1 lifespan module | ✅ Granular |
| T24 | 1 file delete | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram shows | Status |
| ---- | ----------------- | ------------- | ------ |
| T1 | None | Phase 1, no inbound | ✅ Match |
| T2 | None | Phase 1, no inbound | ✅ Match |
| T3 | None | Phase 1, no inbound | ✅ Match |
| T4 | None | Phase 1, no inbound | ✅ Match |
| T5 | None | Phase 1, no inbound | ✅ Match |
| T6 | None | Phase 1, no inbound | ✅ Match |
| T7 | None | Phase 1, no inbound | ✅ Match |
| T8 | T6 | T6 → T8 | ✅ Match |
| T9 | T1, T2, T8 | T8 → T9 (T1/T2 already Phase 1) | ✅ Match |
| T10 | T5, T7 | T5,T7 → T10 | ✅ Match |
| T11 | T5, T7, T9 | T9 → T11 (T5/T7 Phase 1) | ✅ Match |
| T12 | T4, T7 | T4,T7 → T12 | ✅ Match |
| T13 | T2, T3, T5 | T2,T3,T5 → T13 | ✅ Match |
| T14 | T7, T10, T11 | T10 and T11 → T14 (T7 Phase 1) | ✅ Match |
| T15 | T2, T5 | T2,T5 → T15 | ✅ Match |
| T16 | T14 | T14 → T16 | ✅ Match |
| T17 | T14 | T14 → T17 | ✅ Match |
| T18 | T5, T13 | T13 → T18 (T5 Phase 1) | ✅ Match |
| T19 | T5, T12 | T12 → T19 (T5 Phase 1) | ✅ Match |
| T20 | T5, T12 | T12 → T20 (T5 Phase 1) | ✅ Match |
| T21 | T4 | T4 → T21 | ✅ Match |
| T22 | T14, T15, T16, T17, T18, T19, T20 | those → T22 | ✅ Match |
| T23 | T22 | T22 → T23 | ✅ Match |
| T24 | T11, T14 | T11,T14 → T24 | ✅ Match |

Phase-2 `[P]` tasks T10, T12, T13, T15, T21 do not depend on each other. Phase-3 `[P]` groups only share completed deps, not each other. T24 `[P]` with T22, not with T23.

---

## Test Co-location Validation

`.specs/codebase/TESTING.md` does not exist. Project decision (v1 tasks + STATE): automated tests deferred.

| Task | Code layer | Matrix requires | Task says | Status |
| ---- | ---------- | --------------- | --------- | ------ |
| T1–T24 | app / graph / adapters / UI | none (no matrix; deferred) | none | ✅ OK |

No task uses “tested in another task” as a deferral of a required type.
