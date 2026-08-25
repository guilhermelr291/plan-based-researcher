# Plan-Based Researcher

**Vision:** A multi-agent AI researcher that plans first, then executes step by step. A planner agent produces the research plan; an orchestrator loop assigns each step, evaluates the result, and either retries with feedback or advances.
**For:** General users who need structured research rather than a single-shot LLM answer.
**Solves:** One-pass research is shallow, poorly sequenced, and hard to correct. A plan-based loop with evaluation at every step produces more reliable, iterative results.

## Goals

- Ship a FastAPI backend that runs the full pipeline: **plan → execute → analyze** for a user research query.
- The orchestrator must evaluate every step and either send feedback for a retry or proceed to the next step.
- A planner agent generates the plan; specialist agents execute assigned steps using OpenAI and Tavily.

## Tech Stack

**Core:**

- Language: Python
- API: FastAPI
- Agent orchestration: LangGraph
- LLM / tools: LangChain, OpenAI, Tavily

**Key dependencies:** LangChain, LangGraph, FastAPI, OpenAI SDK (via LangChain), Tavily search

## Scope

**v1 includes:**

- Backend only (HTTP API)
- Planner agent that generates a research plan from a user query
- Orchestrator as a loop: assign step → execute → evaluate → retry with feedback **or** advance
- Execute phase: agents complete assigned research steps with OpenAI + Tavily
- Analyze phase: aggregate execution results into a final research output (format TBD)

**Explicitly out of scope:**

- Frontend / UI
- Auth, multi-user accounts, and billing
- Persistent memory across research sessions
- Mobile or desktop clients

## Constraints

- All project artifacts (code, docs, comments, API contracts, prompts) must be in **English**.
- LLM provider: OpenAI.
- Search: Tavily.
- Analyze output shape is **not decided** — specify it before implementing the analyze step.
