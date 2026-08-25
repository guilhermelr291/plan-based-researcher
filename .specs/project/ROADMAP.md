# Roadmap

**Current Milestone:** Foundation
**Status:** Planning

---

## Foundation

**Goal:** Runnable FastAPI app with config for OpenAI and Tavily, ready for the agent graph.
**Target:** App starts, health check works, secrets are loaded from environment.

### Features

**API Skeleton** - PLANNED

- FastAPI application and project layout
- Environment-based config (OpenAI, Tavily)
- Health endpoint

---

## Plan

**Goal:** A user query becomes a structured research plan produced by a planner agent.
**Target:** Given a query, the API (or graph node) returns a plan with ordered steps.

### Features

**Planner Agent** - PLANNED

- Accept a research query
- Generate an ordered plan of research steps
- Structured plan schema the orchestrator can consume

---

## Execute

**Goal:** The orchestrator loop runs each plan step, evaluates the result, and retries or advances.
**Target:** A plan can be executed end-to-end with per-step evaluation and bounded retries.

### Features

**Orchestrator Loop** - PLANNED

- Assign the current step to the appropriate agent
- Evaluate the step result
- On failure/quality miss: feedback + retry
- On success: advance to the next step
- Stop when the plan is complete or retry limit is reached

**Research Execution** - PLANNED

- Agents execute assigned steps using OpenAI
- Web research via Tavily
- Step outputs stored for later analysis

---

## Analyze

**Goal:** Turn executed step results into a final research response from the backend.
**Target:** Pipeline returns a completed research result after analyze. Output format still TBD.

### Features

**Result Analysis** - PLANNED

- Aggregate step outputs
- Produce the final research result
- Expose the result through the FastAPI API

---

## End-to-End Research API

**Goal:** One backend entry point runs plan → execute → analyze and returns the result.
**Target:** A single research request completes the full pipeline.

### Features

**Research Endpoint** - PLANNED

- Accept a research query
- Run the LangGraph pipeline
- Return plan, execution trace (as needed), and final analysis

---

## Future Considerations

- Frontend / UI
- User accounts and history
- Streaming progress of the orchestrator loop
- Analyze output format (markdown report, JSON, citations — undecided)
- Persistent session memory
