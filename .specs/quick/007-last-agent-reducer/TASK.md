# Quick Task 007: last_agent reducer for search waves

**Date:** 2026-08-30
**Status:** Done

## Description

Fix `InvalidUpdateError` on `last_agent` when parallel `Send("search")` workers each write that key in the same superstep.

## Files Changed

- `src/plan_based_researcher/graph/state.py` — `last_write` reducer on `last_agent`

## Verification

- [x] `last_write` returns the newest scalar
- [x] Compiled `StateGraph(GraphState)` with two parallel nodes writing `last_agent` completes without `InvalidUpdateError`
- [x] Result `last_agent` is `"search"`

## Commit

`2673a51` — `fix(graph): reduce last_agent on parallel search writes`
