# State

**Last Updated:** 2026-08-25
**Current Work:** Dependencies installed — ready to specify first feature

---

## Recent Decisions (Last 60 days)

### AD-001: Plan-based multi-agent researcher (2026-08-25)

**Decision:** Build an AI researcher where a planner agent generates the plan and an orchestrator loop assigns, evaluates, and retries or advances each step.
**Reason:** Plan-based control with per-step evaluation is the core product approach.
**Trade-off:** More moving parts than a single LLM call; slower and more token-heavy.
**Impact:** LangGraph graph is a loop around execute + evaluate, not a linear chain only.

### AD-002: v1 is backend-only (2026-08-25)

**Decision:** v1 ships FastAPI + LangGraph only. Pipeline is plan → execute → analyze.
**Reason:** Prove the agent loop before investing in UI.
**Trade-off:** No user-facing product until a client exists.
**Impact:** All v1 features are API and graph nodes.

### AD-003: Stack — Python, FastAPI, LangChain, LangGraph, OpenAI, Tavily (2026-08-25)

**Decision:** Use this stack for the backend and agents.
**Reason:** User-selected; OpenAI for LLM, Tavily for search.
**Trade-off:** Tied to those vendors; no local/offline research in v1.
**Impact:** Config, secrets, and tools assume OpenAI + Tavily.

### AD-004: Project language is English (2026-08-25)

**Decision:** All project artifacts (code, docs, comments, API, prompts) are in English.
**Reason:** User requirement.
**Trade-off:** None material.
**Impact:** Specs, identifiers, and prompts stay in English.

---

## Active Blockers

None.

---

## Lessons Learned

None yet.

---

## Quick Tasks Completed

| #   | Description | Date | Commit | Status |
| --- | ----------- | ---- | ------ | ------ |
| 001 | Install v1 stack (FastAPI, LangGraph, LangChain, OpenAI, Tavily) via uv | 2026-08-25 | — | ✅ Done |

---

## Deferred Ideas

- [ ] Analyze output format (markdown, JSON, citations, quality score) — Captured during: project init. Specify before implementing Analyze.
- [ ] Frontend / UI — Captured during: project init (explicitly out of v1)
- [ ] Auth, multi-user, billing — Captured during: project init
- [ ] Persistent memory across sessions — Captured during: project init
- [ ] Streaming orchestrator progress — Captured during: roadmap

---

## Todos

- [ ] Decide analyze output contract before specifying the Analyze feature

---

## Preferences

**Model Guidance Shown:** never
