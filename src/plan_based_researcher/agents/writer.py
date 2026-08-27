"""Writer runner: grounded markdown from numbered chunks (GROUND-01–03)."""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from plan_based_researcher.agents.registry import REGISTRY
from plan_based_researcher.api.schemas import Citation
from plan_based_researcher.graph.state import EvidenceChunk, GraphState
from plan_based_researcher.policy import Policy

__all__ = ["WriterOutput", "WriterRunner"]


class WriterOutput(BaseModel):
    markdown: str = Field(description="Student-facing markdown that cites evidence as [n]")
    citation_ns: list[int] = Field(
        default_factory=list,
        description="The [n] indices actually used in markdown",
    )


def _format_chunks(chunks: list[EvidenceChunk]) -> str:
    """Format chunks as ``[n] arXiv:{id} — {title} ({year})\\n{excerpt}`` (GROUND-01)."""
    if not chunks:
        return "(no evidence chunks provided)"
    blocks: list[str] = []
    for chunk in chunks:
        n = chunk["n"]
        arxiv_id = chunk["arxiv_id"]
        title = chunk["title"]
        year = chunk["year"]
        excerpt = chunk["excerpt"]
        blocks.append(f"[{n}] arXiv:{arxiv_id} — {title} ({year})\n{excerpt}")
    return "\n\n".join(blocks)


def _citations_from_chunks(chunks: list[EvidenceChunk]) -> list[dict]:
    return [
        Citation(
            n=chunk["n"],
            arxiv_id=chunk["arxiv_id"],
            title=chunk["title"],
            year=chunk["year"],
            url=chunk["url"],
            excerpt=chunk["excerpt"],
            chunk_id=chunk["chunk_id"],
        ).model_dump()
        for chunk in chunks
    ]


def _language(state: GraphState) -> str:
    gate = state.get("gate") or {}
    return str(gate.get("language") or "")


def _current_task(state: GraphState) -> str:
    plan = state.get("plan") or []
    index = state.get("step_index") or 0
    if not plan or index < 0 or index >= len(plan):
        return ""
    step = plan[index]
    if isinstance(step, dict):
        return str(step.get("task") or "")
    return ""


def _eval_feedback(state: GraphState) -> str:
    last_eval = state.get("last_eval") or {}
    return str(last_eval.get("feedback") or "")


def _system_prompt() -> str:
    return (
        f"{REGISTRY['writer'].abilities}\n\n"
        f"Grounding rule: {Policy.GROUNDING_RULE}.\n\n"
        "You are given a numbered list of arXiv evidence chunks formatted as [n] blocks. "
        "Cite only those [n] values; never invent indices or non-arXiv sources. "
        "Every technical claim needs a real [n]. "
        "Match the student query language and a student didactic register. "
        "If chunks disagree or conflict, include a limitations/contradictions section; "
        "do not pick a silent winner. State both sides with their [n] citations."
    )


def _user_prompt(state: GraphState, formatted_chunks: str) -> str:
    language = _language(state)
    task = _current_task(state)
    feedback = _eval_feedback(state)
    parts = [
        f"Student query:\n{state.get('query') or ''}",
    ]
    if language:
        parts.append(f"Answer language: {language}")
    if task:
        parts.append(f"Current writing task:\n{task}")
    if feedback:
        parts.append(f"Evaluator feedback (honor this on retry):\n{feedback}")
    parts.append(f"Evidence chunks:\n{formatted_chunks}")
    return "\n\n".join(parts)


class WriterRunner:
    def __init__(self, api_key: str | None = None) -> None:
        kwargs: dict = {"model": REGISTRY["writer"].model}
        if api_key is not None:
            kwargs["api_key"] = api_key
        self._llm = ChatOpenAI(**kwargs).with_structured_output(WriterOutput)

    async def run(self, state: GraphState) -> dict:
        chunks: list[EvidenceChunk] = list(state.get("evidence_chunks") or [])
        formatted = _format_chunks(chunks)
        output = await self._llm.ainvoke(
            [
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": _user_prompt(state, formatted)},
            ]
        )
        markdown = output.markdown if isinstance(output, WriterOutput) else str(output)
        return {
            "writer_markdown": markdown,
            "citations": _citations_from_chunks(chunks),
            "last_agent": "writer",
        }
