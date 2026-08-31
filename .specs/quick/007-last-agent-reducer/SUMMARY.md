# Summary: 007 last_agent reducer for search waves

**Date:** 2026-08-30
**Status:** Done

## What changed

Parallel `Send("search")` workers all return `last_agent: "search"` in the same superstep. `last_agent` was a last-value channel, so LangGraph raised `InvalidUpdateError`. It is now `Annotated[str, last_write]` so concurrent writes keep the newest value (all search workers write the same string).

## Verification

- `last_write("planner", "search") == "search"`
- Two-node fan-out on `StateGraph(GraphState)` invoking `{"last_agent": "planner"}` returned `last_agent == "search"` without error

## Commit

`fix(graph): reduce last_agent on parallel search writes`
