# Admission 1/topic and Per-Paper Retrieve Tasks

**Design**: `.specs/features/admission-retrieve-per-topic/design.md`  
**Routing atlas**: `.specs/features/admission-retrieve-per-topic/graph-flow.md`  
**Status**: Implemented (T1–T15)

Automated tests (pytest, Testcontainers, e2e) are **out of scope**, same as v1 and `orchestrator-eval-replan`. There is no `.specs/codebase/TESTING.md`. Done-when is implementation complete vs the approved design. Spec “Independent Test” lines stay as later manual UAT, not Execute work.

No new graph nodes, no new SSE event names, no hybrid adapter rewrite, no picker LLM.

---

## Execution Plan

### Phase 1: Types and policy (all `[P]`)

```
T1 [P]  T2 [P]  T3 [P]  T4 [P]
```

### Phase 2: Isolated modules (all `[P]` after their Phase 1 deps)

```
T1 ──→ T5 [P]
T2 ──→ T6 [P]
T2 ──→ T7 [P]
T1,T3 ──→ T9 [P]
T3 ──→ T15 [P]
T1,T4 ──→ T12 [P]
T1,T3 ──→ T13 [P]
```

T5, T6, T7, T9, T12, T13, T15 do **not** share files.

### Phase 3: Search eval node + retrieve strategy

```
T3,T6,T7 ──→ T8
T3,T7 ──→ T10 [P] with T8
```

T8 is `evaluate.py`. T10 is `strategies.py` (after T7). Different files → `[P]`.

### Phase 4: Retrieve routing + writer eval

```
T8,T10 ──→ T11
T10,T13 ──→ T14 [P] with T11
```

T11 is `evaluate.py` (after T8). T14 is `strategies.py` (after T10). Different files → `[P]`.

`strategies.py` order is **T7 → T10 → T14** (never parallel with each other).  
`evaluate.py` order is **T8 → T11** (never parallel with each other).

---

## Task Breakdown

### T1: Policy search pool, per-paper k, hole rule [P]

**What**: Add `search_max_results=8`, `retrieve_k_per_paper=3`, `HOLE_RULE`; delete `retrieve_k`.
**Where**: `src/plan_based_researcher/policy.py`
**Depends on**: None
**Reuses**: existing `Policy` class, `GROUNDING_RULE`
**Requirement**: ADM-02, RETR-02, WRITE-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `Policy.search_max_results == 8` (not reused as `max_papers`)
- [x] `Policy.retrieve_k_per_paper == 3`
- [x] `Policy.retrieve_k` attribute is gone
- [x] `HOLE_RULE` states: absence sentence needs no `[n]`; technical claims about a topic need chunks from **that** topic’s paper; no parametric fill; do not cite another method’s chunks as the missing topic
- [x] `max_papers`, hybrid weights, splitter, retries, replans unchanged

**Tests**: none
**Gate**: none

**Verify**: `python -c "from plan_based_researcher.policy import Policy; assert Policy.search_max_results==8; assert Policy.retrieve_k_per_paper==3; assert not hasattr(Policy,'retrieve_k')"`

**Commit**: `feat(admission): add search pool, per-paper k, and hole rule`

---

### T2: PaperKey and verdict ranked_keys [P]

**What**: Add `PaperKey`; add `ranked_keys: list[PaperKey] = []` on `SearchStepVerdict`.
**Where**: `src/plan_based_researcher/eval/types.py`
**Depends on**: None
**Reuses**: existing `SearchStepVerdict` / `SearchWaveJudgement`
**Requirement**: ADM-03

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `PaperKey` has `arxiv_id: str` and `version: str = ""`
- [x] `SearchStepVerdict.ranked_keys` defaults to `[]`
- [x] Other verdict fields unchanged (`step_index`, `passed`, `plan_inadequate`, `feedback`)

**Tests**: none
**Gate**: none

**Verify**: `python -c "from plan_based_researcher.eval.types import PaperKey, SearchStepVerdict; assert SearchStepVerdict(step_index=0,passed=True,feedback='').ranked_keys==[]"`

**Commit**: `feat(admission): add ranked_keys to search verdict`

---

### T3: Graph state ranked_keys and retrieve_ingest [P]

**What**: Add `RankedKey`, optional `ranked_keys` on `SearchArtifact`, `RetrieveIngestReport`, and `retrieve_ingest` on `GraphState`.
**Where**: `src/plan_based_researcher/graph/state.py`
**Depends on**: None
**Reuses**: existing `SearchArtifact`, `merge_search_artifacts`, `merge_papers`
**Requirement**: ADM-03, RETR-04

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `RankedKey` TypedDict: `arxiv_id`, `version`
- [x] `SearchArtifact.ranked_keys` is `NotRequired[list[RankedKey]]`
- [x] `RetrieveIngestReport` has `case: Literal["t1","t2a","t3"]`, `gap_step_indices: list[int]`, `walked: bool`
- [x] `GraphState.retrieve_ingest` is an overwrite field (no reducer)
- [x] `merge_papers` / `merge_search_artifacts` unchanged (last-write-wins whole artifact)
- [x] `eval_next` stays on `GraphState`

**Tests**: none
**Gate**: none

**Verify**: `GraphState.__annotations__` includes `retrieve_ingest`; `SearchArtifact` accepts artifacts without `ranked_keys`.

**Commit**: `feat(admission): add ranked_keys and retrieve_ingest to graph state`

---

### T4: Registry 1/topic, per-paper retrieve, hole abilities [P]

**What**: Update `search` / `retrieve` / `writer` / `planner` abilities text only (no roster change).
**Where**: `src/plan_based_researcher/agents/registry.py`
**Depends on**: None
**Reuses**: existing `REGISTRY`, `PLAN_AGENTS`
**Requirement**: ADM-01, RETR-02, WRITE-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Search abilities: one named topic; ranking is at eval; runner does not pick a paper; no PDF
- [x] Retrieve abilities: walk `ranked_keys`, one usable PDF per ranking, hybrid `k=3` per paper, no arXiv search
- [x] Writer abilities: include hole rule (no parametric fill; announce missing topic)
- [x] Planner abilities: each search is one named topic (distinct tasks on compare)
- [x] `PLAN_AGENTS` and models/tools unchanged

**Tests**: none
**Gate**: none

**Verify**: `PLAN_AGENTS == frozenset({"search","retrieve","writer"})`; abilities mention ranking / per-paper k / hole.

**Commit**: `feat(admission): update registry abilities for 1/topic and hole`

---

### T5: Search API pool search_max_results [P]

**What**: Call arXiv with `Policy.search_max_results` (never `max_papers`, never 1). Still artifacts only.
**Where**: `src/plan_based_researcher/agents/search.py`
**Depends on**: T1
**Reuses**: existing formulate + allowlist + recency + dedupe
**Requirement**: ADM-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `search(..., max_results=Policy.search_max_results)`
- [x] Return dict still has `search_artifacts` only (no `papers`)
- [x] No champion picker in this runner

**Tests**: none
**Gate**: none

**Verify**: Grep `search.py` for `search_max_results`; no `Policy.max_papers` on the API call; no `load_pdf_text`.

**Commit**: `feat(admission): search uses search_max_results pool`

---

### T6: Admission clip and U1 helpers [P]

**What**: New `eval/admission.py` with clip, champion seed, U1, and `finalize_wave_rankings`.
**Where**: `src/plan_based_researcher/eval/admission.py`
**Depends on**: T2
**Reuses**: `PaperKey` from `eval/types.py`
**Requirement**: ADM-03, ADM-04

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `hit_key`, `clip_ranked_keys`, `champion_keys`, `apply_u1`, `finalize_wave_rankings` match the design signatures
- [x] Clip keeps keys present in **that** artifact’s hits, judge order; empty `version` binds only if exactly one hit shares `arxiv_id`
- [x] `assigned` seed = heads of passed searches **not in this wave**; each passing step adds **head only**
- [x] Empty after clip+U1 → `passed=False`; non-empty → `passed=True`
- [x] Deterministic-empty steps stay empty ranking; `plan_inadequate` / `feedback` copied from the judge
- [x] This module does not call an LLM and is not used from `SearchRunner`

**Tests**: none
**Gate**: none

**Verify**: `from plan_based_researcher.eval.admission import finalize_wave_rankings` succeeds; module has no `ChatOpenAI` import.

**Commit**: `feat(admission): add clip and U1 ranking helpers`

---

### T7: Search wave judge returns rankings [P]

**What**: Checklist asks for ordered `ranked_keys`; deterministic fail forces empty `ranked_keys` (still one LLM call). No U1 here.
**Where**: `src/plan_based_researcher/eval/strategies.py` (`SearchEvalStrategy` / `_merge_wave_verdicts` / `_search_checklist` only)
**Depends on**: T2
**Reuses**: existing one-call `evaluate_wave`, `_search_deterministic`
**Requirement**: ADM-03

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Checklist tells the judge to output an ordered list of acceptable `(arxiv_id, version)` per step
- [x] `_merge_wave_verdicts` on deterministic fail: `passed=False`, `ranked_keys=[]`, keep judge `plan_inadequate` / `feedback`
- [x] U1 / clip are **not** applied in this strategy
- [x] Still one structured `SearchWaveJudgement` call per wave

**Tests**: none
**Gate**: none

**Verify**: `_search_checklist` mentions `ranked_keys`; `_merge_wave_verdicts` does not import `eval.admission`.

**Commit**: `feat(admission): search judge returns ranked_keys`

---

### T8: Search evaluate persist rankings, LOOP-04, no papers

**What**: Apply `finalize_wave_rankings`; write `ranked_keys` on the full artifact; never admit hits into `papers`; search fail always `_retry_status`.
**Where**: `src/plan_based_researcher/graph/nodes/evaluate.py` (`_evaluate_wave` only)
**Depends on**: T3, T6, T7
**Reuses**: `_emit_eval`, `_apply_route`, `_retry_status`, `eval_next`
**Requirement**: ADM-01, ADM-03, ADM-04, LOOP-04

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] No `update["papers"]` / `_paper_refs(hits)` on search pass
- [x] Passed steps persist `search_artifacts[str(i)]` with `hits`, `query_used`, and `ranked_keys`
- [x] `passed` comes from finalized ranking (non-empty after clip+U1), not raw judge `passed`
- [x] Search fail never uses `elif plan_inadequate: need_replan`; always `_retry_status` (attempt 1 → dispatch, attempt 2 → replan)
- [x] `plan_inadequate` still stored on `eval_by_step` / SSE `eval` frames
- [x] Mixed wave: replan still wins over retry via existing `_apply_route`

**Tests**: none
**Gate**: none

**Verify**: Grep `_evaluate_wave` for `papers` assignment is gone; `finalize_wave_rankings` is called; `plan_inadequate` is not a search routing branch.

**Commit**: `feat(admission): persist ranked_keys and always retry search attempt 1`

---

### T9: Retrieve walk, ingest, per-paper hybrid [P]

**What**: Ranking walk (one usable PDF per passed search), `merge_papers` before hybrid, per-paper `k=3` slice+concat, `retrieve_ingest` report.
**Where**: `src/plan_based_researcher/agents/retrieve.py`
**Depends on**: T1, T3
**Reuses**: existing formulate, splitter 500/100, `load_pdf_text`, upsert, `HybridRetrievePort.retrieve`, `merge_papers`
**Requirement**: RETR-02, RETR-03, RETR-04, ADM-01, ADM-04

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `retry_counts[str(retrieve_index)] > 0` → skip walk; hybrid `state.papers` only
- [x] No passed `search` on current plan → skip walk; unique thread papers (cap `max_papers`)
- [x] Walk: plan order; skip keys already in `usable`; cache hit or PDF; empty extract → next key same ranking; at most one admit per ranking; gap if exhausted
- [x] `merged = merge_papers(state.papers, newly_admitted)` before hybrid
- [x] T1 (`merged` empty): skip formulate and hybrid; `evidence_chunks=[]`; `case="t1"`
- [x] Else: formulate when hybrid runs; for each merged paper `hybrid.retrieve(query, [that_key], k=retrieve_k_per_paper)` then slice `[:retrieve_k_per_paper]`; concat; continuous `[n]` from 1
- [x] `case="t2a"` if gaps and merged non-empty; `case="t3"` if no gaps (including follow-up)
- [x] Return `retrieve_ingest`; `papers` only for newly admitted this execute (omit on skip-walk / T3 retry)
- [x] No union `hybrid.retrieve(query, all_keys, k=...)`; no `Policy.retrieve_k`

**Tests**: none
**Gate**: none

**Verify**: Grep `retrieve.py` for `retrieve_k_per_paper` and a loop over papers; no `Policy.retrieve_k`; no `PaperPort.search`.

**Commit**: `feat(admission): retrieve walks rankings and hybrids per paper`

---

### T10: Retrieve eval T1/T2a short-circuit [P]

**What**: T1/T2a skip the mini-judge (`fail` + `plan_inadequate`); T3 keeps chunk checks then semantic judge.
**Where**: `src/plan_based_researcher/eval/strategies.py` (`RetrieveEvalStrategy` only)
**Depends on**: T3, T7
**Reuses**: existing `_deterministic` admitted-key checks, `_judge_task`
**Requirement**: RETR-04

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `retrieve_ingest.case == "t1"` → `EvalResult(status="fail", plan_inadequate=True)` without LLM
- [x] `case == "t2a"` → same (chunks already produced by retrieve execute)
- [x] `case == "t3"` → existing empty/foreign-chunk then semantic judge vs retrieve `task`
- [x] Checklist notes T3 query miss is a retrieve rewrite, not a new PDF walk
- [x] Does not remove searches from `passed_steps`

**Tests**: none
**Gate**: none

**Verify**: `RetrieveEvalStrategy.evaluate` branches on `retrieve_ingest` before `_judge_task` for t1/t2a.

**Commit**: `feat(admission): retrieve eval short-circuits T1 and T2a`

---

### T11: Retrieve evaluate LOOP-05 / R2

**What**: T3 query miss on attempt 1 always retries (ignore judge `plan_inadequate` for the edge); paper-set inadequate skips leftover retry.
**Where**: `src/plan_based_researcher/graph/nodes/evaluate.py` (`_evaluate_step` retrieve branch)
**Depends on**: T8, T10
**Reuses**: `_retry_status`, `_apply_route` (T1/T2a already skip retry via `plan_inadequate`)
**Requirement**: LOOP-05, RETR-04

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `agent=="retrieve"` and `case=="t3"` and **query miss** (empty chunks, foreign chunk, or off-task empty/off-task fail) and attempt 1 → retry even if `plan_inadequate`
- [x] T3 **paper-set inadequate** (ingest complete, chunks non-empty, all admitted keys, judge `plan_inadequate`, not empty/off-task) → skip leftover retry → replan or `insufficient`
- [x] T3 attempt 2 exhausted → replan remaining or `insufficient`
- [x] T1/T2a still use existing `plan_inadequate` skip-retry (no retrieve query retry)
- [x] Writer path unchanged except it still runs after this function

**Tests**: none
**Gate**: none

**Verify**: `_evaluate_step` has an explicit retrieve T3 branch; search LOOP-04 in `_evaluate_wave` is untouched.

**Commit**: `feat(admission): retrieve T3 query miss always retries once`

---

### T12: Planner 1/topic and S8a / T1 / T2a / T3 constraints [P]

**What**: Initial prompt 1/topic; replan prompt injects per-leftover S8a plus retrieve T1/T2a/T3 rules; prefix shows champion title.
**Where**: `src/plan_based_researcher/agents/planner.py`
**Depends on**: T1, T4
**Reuses**: `replan_remaining`, `planner_prompt_abilities()`, prefix packing in `replan.py` (do not change the node)
**Requirement**: ADM-01, REPLAN-03

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Initial prompt: each `search` is one named topic (distinct `task` texts on compare)
- [x] Replan: **per leftover search index**, `eval_by_step[i].plan_inadequate` true → MUST NOT emit a new search for that topic; false → MUST emit one corrected search
- [x] Retrieve T2a: prefer writer-only when `evidence_chunks` non-empty; living `[n]` + no usable paper for gapped tasks; no memory fill
- [x] Retrieve T1: MUST NOT emit a new search
- [x] Retrieve T3 exhausted: rewrite remaining, usually Writer `task`
- [x] Prefix summary uses `ranked_keys[0]` title (fallback to task if missing), not five raw hits
- [x] `graph/nodes/replan.py` packing unchanged

**Tests**: none
**Gate**: none

**Verify**: `replan_remaining` prompt contains S8a / T1 / T2a / T3 constraints; `replan.py` has no new enum.

**Commit**: `feat(admission): planner S8a and retrieve replan constraints`

---

### T13: Writer living vs missing and HOLE_RULE [P]

**What**: Derive living/missing topics from state; put `HOLE_RULE` on the system prompt and lists on the user prompt.
**Where**: `src/plan_based_researcher/agents/writer.py`
**Depends on**: T1, T3
**Reuses**: existing `WriterOutput`, `_system_prompt` / `_user_prompt`, citation mapping
**Requirement**: WRITE-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] Helper (same module, importable) lists **living** (passed search whose ingested key is in `papers` and has ≥1 chunk) with those `[n]`, and **missing** (unpassed leftover search tasks + T2a `gap_step_indices` tasks)
- [x] System prompt includes `Policy.HOLE_RULE` and `GROUNDING_RULE`
- [x] User prompt includes living vs missing lists
- [x] Retry still uses the same `evidence_chunks`
- [x] ORCH-03 citation mapping unchanged

**Tests**: none
**Gate**: none

**Verify**: Writer module imports `Policy.HOLE_RULE`; helper is importable from `eval/strategies.py` without circular import (if circular, move helper to a tiny `eval/coverage.py` in this same task).

**Commit**: `feat(admission): writer prompt states living topics and holes`

---

### T14: Writer eval WRITE-02 hole judge [P]

**What**: Language/tone judge receives living/missing lists and fails parametric fill / mis-cite; keep ORCH-03 deterministic `[n]`.
**Where**: `src/plan_based_researcher/eval/strategies.py` (`WriterEvalStrategy` only)
**Depends on**: T10, T13
**Reuses**: existing deterministic `[n]` + arxiv.org URL checks
**Requirement**: WRITE-02

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `_writer_checklist` / judge human message includes living vs missing from the T13 helper
- [x] Judge must fail: definition/mechanism/comparison of a missing topic; citing living `[n]` as the missing topic
- [x] Absence sentence without `[n]` is allowed by the checklist (deterministic still requires ≥1 real `[n]` when chunks exist)
- [x] Empty chunks still fail deterministic ORCH-03 (T1 writer)
- [x] No new `EvalResult` status values

**Tests**: none
**Gate**: none

**Verify**: `WriterEvalStrategy._judge_language_and_tone` includes living/missing; `EvalResult.status` literals unchanged.

**Commit**: `feat(admission): writer eval enforces hole rule`

---

### T15: Initial graph state retrieve_ingest [P]

**What**: Default `retrieve_ingest` on new `POST /research` threads so old `.get()` paths are not required on first hop.
**Where**: `src/plan_based_researcher/api/routes.py`
**Depends on**: T3
**Reuses**: existing `_initial_state`
**Requirement**: RETR-04

**Tools**: MCP NONE · Skill NONE

**Done when**:

- [x] `_initial_state` sets `retrieve_ingest` to `{"case": "t3", "gap_step_indices": [], "walked": False}`
- [x] No new SSE event names; request body unchanged

**Tests**: none
**Gate**: none

**Verify**: Grep `_initial_state` for `retrieve_ingest`.

**Commit**: `feat(admission): default retrieve_ingest on new threads`

---

## Parallel Execution Map

```
Phase 1 (all [P]):
  T1  T2  T3  T4

Phase 2 (all [P], different files):
  T1 → T5 search.py
  T2 → T6 admission.py
  T2 → T7 strategies.py (SearchEvalStrategy)
  T1,T3 → T9 retrieve.py
  T3 → T15 routes.py
  T1,T4 → T12 planner.py
  T1,T3 → T13 writer.py

Phase 3:
  T3,T6,T7 → T8 evaluate.py (_evaluate_wave)
  T3,T7 → T10 strategies.py (RetrieveEvalStrategy)   [P] with T8

Phase 4:
  T8,T10 → T11 evaluate.py (_evaluate_step)
  T10,T13 → T14 strategies.py (WriterEvalStrategy)   [P] with T11
```

**File serialization (do not parallelize):**

- `eval/strategies.py`: T7 → T10 → T14
- `graph/nodes/evaluate.py`: T8 → T11

**Parallelism constraint:** `[P]` tasks in the same phase do not share a file and do not depend on each other.

---

## Requirement Traceability (tasks)

| ID | Tasks |
| -- | ----- |
| ADM-01 | T4, T8, T9, T12 |
| ADM-02 | T1, T5 |
| ADM-03 | T2, T6, T7, T8 |
| ADM-04 | T6, T8, T9 |
| RETR-02 | T1, T4, T9 |
| RETR-03 | T9 |
| RETR-04 | T3, T9, T10, T11, T15 |
| LOOP-04 | T8 |
| LOOP-05 | T11 |
| REPLAN-03 | T12 |
| WRITE-02 | T1, T4, T13, T14 |

**Coverage:** 11/11 spec IDs have ≥1 task. 0 unmapped tasks without a requirement.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1 | 1 class (`policy.py`) | ✅ Granular |
| T2 | 1 types module | ✅ Granular |
| T3 | 1 state module | ✅ Granular |
| T4 | 1 registry abilities text | ✅ Granular |
| T5 | 1 runner call site | ✅ Granular |
| T6 | 1 new helper module | ✅ Granular |
| T7 | SearchEvalStrategy in `strategies.py` | ✅ Granular |
| T8 | `_evaluate_wave` only | ✅ Granular |
| T9 | 1 runner (`retrieve.py`; walk+hybrid cohesive) | ✅ Granular |
| T10 | RetrieveEvalStrategy only | ✅ Granular |
| T11 | `_evaluate_step` retrieve branch | ✅ Granular |
| T12 | 1 planner module | ✅ Granular |
| T13 | 1 writer module | ✅ Granular |
| T14 | WriterEvalStrategy only | ✅ Granular |
| T15 | 1 initial-state dict | ✅ Granular |

T7 / T10 / T14 are three edits to one file but **serialized**, not one mega-task. T8 / T11 same for `evaluate.py`.

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram shows | Status |
| ---- | ----------------- | ------------- | ------ |
| T1 | None | Phase 1, no inbound | ✅ Match |
| T2 | None | Phase 1, no inbound | ✅ Match |
| T3 | None | Phase 1, no inbound | ✅ Match |
| T4 | None | Phase 1, no inbound | ✅ Match |
| T5 | T1 | T1 → T5 | ✅ Match |
| T6 | T2 | T2 → T6 | ✅ Match |
| T7 | T2 | T2 → T7 | ✅ Match |
| T8 | T3, T6, T7 | T3,T6,T7 → T8 | ✅ Match |
| T9 | T1, T3 | T1,T3 → T9 | ✅ Match |
| T10 | T3, T7 | T3,T7 → T10 | ✅ Match |
| T11 | T8, T10 | T8,T10 → T11 | ✅ Match |
| T12 | T1, T4 | T1,T4 → T12 | ✅ Match |
| T13 | T1, T3 | T1,T3 → T13 | ✅ Match |
| T14 | T10, T13 | T10,T13 → T14 | ✅ Match |
| T15 | T3 | T3 → T15 | ✅ Match |

Phase-2 `[P]` tasks T5, T6, T7, T9, T12, T13, T15 do not depend on each other. Phase-3 `[P]` pair T8/T10 do not depend on each other. Phase-4 `[P]` pair T11/T14 do not depend on each other.

---

## Test Co-location Validation

`.specs/codebase/TESTING.md` does not exist. Project decision (v1 tasks + STATE): automated tests deferred.

| Task | Code layer | Matrix requires | Task says | Status |
| ---- | ---------- | --------------- | --------- | ------ |
| T1–T15 | policy / eval / graph / agents / API | none (no matrix; deferred) | none | ✅ OK |

No task uses “tested in another task” as a deferral of a required type.

---

## Confirm before Execute

Executed 2026-08-30. User asked to Execute the draft list. Fifteen tasks, no new LangGraph nodes, hybrid adapter untouched. `strategies.py` serialized T7 → T10 → T14; `evaluate.py` serialized T8 → T11. Tests remain deferred. T13 helper stayed in `writer.py` (no circular import).
