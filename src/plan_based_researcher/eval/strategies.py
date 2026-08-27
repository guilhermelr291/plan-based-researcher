"""Research and writer eval strategies (ORCH-02, ORCH-03, PAT-05)."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Protocol
from urllib.parse import urlparse

from langchain_openai import ChatOpenAI

from plan_based_researcher.eval.types import EvalResult
from plan_based_researcher.graph.state import GraphState
from plan_based_researcher.policy import Policy

__all__ = ["EvalStrategy", "ResearchEvalStrategy", "WriterEvalStrategy"]

_CITATION_RE = re.compile(r"\[(\d+)\]")
_URL_RE = re.compile(r"https?://[^\s\]\)>\"']+", re.IGNORECASE)


class EvalStrategy(Protocol):
    async def evaluate(self, state: GraphState | dict) -> EvalResult: ...


def _as_state(state: GraphState | dict) -> dict:
    return state if isinstance(state, dict) else dict(state)


def _current_step(state: dict) -> dict:
    plan = state.get("plan") or []
    try:
        index = int(state.get("step_index") or 0)
    except (TypeError, ValueError):
        index = 0
    if not isinstance(plan, list) or index < 0 or index >= len(plan):
        return {}
    step = plan[index]
    return step if isinstance(step, dict) else {}


def _paper_published(paper: dict) -> date | datetime | None:
    published_at = paper.get("published_at")
    if isinstance(published_at, (date, datetime)):
        return published_at
    year = paper.get("year")
    if not isinstance(year, int) or year < 1:
        return None
    try:
        return date(year, 12, 31)
    except ValueError:
        return None


def _categories(paper: dict) -> list[str]:
    raw = paper.get("categories") or []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return [str(raw)]


def _chunk_ns(chunks: object) -> set[int]:
    numbers: set[int] = set()
    if not isinstance(chunks, list):
        return numbers
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        n = chunk.get("n")
        if isinstance(n, int):
            numbers.add(n)
        elif isinstance(n, str) and n.isdigit():
            numbers.add(int(n))
    return numbers


def _is_arxiv_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "arxiv.org" or host.endswith(".arxiv.org")


def _writer_checklist() -> str:
    categories = ", ".join(sorted(Policy.arxiv_categories))
    return (
        f"Allowed evidence domain: arXiv categories only ({categories}).\n"
        f"Grounding: {Policy.GROUNDING_RULE}.\n"
        "Answer in the same language as the student query.\n"
        "Use a didactic, student-friendly tone.\n"
        "Do not introduce sources outside the provided evidence chunks or arxiv.org URLs."
    )


class ResearchEvalStrategy:
    """ORCH-02: allowlisted coverage in date policy, aligned to the current step."""

    async def evaluate(self, state: GraphState | dict) -> EvalResult:
        data = _as_state(state)
        papers = data.get("papers") or []
        if not isinstance(papers, list):
            papers = []
        papers = papers[: Policy.max_papers]
        step = _current_step(data)
        historical = bool(step.get("historical", False))
        query = str(data.get("query") or "").strip()
        task = str(step.get("task") or "").strip()

        if not papers:
            return EvalResult(
                status="retry",
                feedback=(
                    "No papers for this step. Search arXiv again using the step task "
                    f"aligned to the query. Task: {task or query or '(missing)'}"
                ),
            )

        qualifying: list[dict] = []
        for paper in papers:
            if not isinstance(paper, dict):
                continue
            if not Policy.is_allowlisted(_categories(paper)):
                continue
            if not Policy.within_recency(
                _paper_published(paper), historical=historical
            ):
                continue
            qualifying.append(paper)

        if not qualifying:
            return EvalResult(
                status="retry",
                feedback=(
                    "Need at least one allowlisted paper within recency "
                    f"(Policy.recency_years={Policy.recency_years}) unless the current "
                    f"step is historical (historical={historical}). "
                    f"Cap considered: Policy.max_papers={Policy.max_papers}."
                ),
            )

        if not query and not task:
            return EvalResult(
                status="retry",
                feedback="Query is empty and the current step has no task to align to.",
            )

        return EvalResult(
            status="pass",
            feedback=(
                "Coverage meets allowlist and date policy for the current step "
                f"(historical={historical}, papers={len(qualifying)})."
            ),
        )


class WriterEvalStrategy:
    """ORCH-03: real [n] citations, query language, student tone, no extra sources."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._judge = None
        if api_key is not None:
            self._judge = ChatOpenAI(
                model="gpt-5-mini", api_key=api_key
            ).with_structured_output(EvalResult, method="json_schema")

    async def evaluate(self, state: GraphState | dict) -> EvalResult:
        data = _as_state(state)
        markdown = data.get("writer_markdown") or ""
        if not isinstance(markdown, str):
            markdown = str(markdown)

        deterministic = self._deterministic(markdown, data.get("evidence_chunks"))
        if deterministic.status != "pass":
            return deterministic

        judged = await self._judge_language_and_tone(data, markdown)
        return judged if judged is not None else deterministic

    def _deterministic(self, markdown: str, chunks: object) -> EvalResult:
        if not markdown.strip():
            return EvalResult(
                status="retry",
                feedback="writer_markdown is empty. Write the student answer with real [n] citations.",
            )

        cited = [int(match.group(1)) for match in _CITATION_RE.finditer(markdown)]
        if not cited:
            return EvalResult(
                status="retry",
                feedback=(
                    f"No [n] citations found. {Policy.GROUNDING_RULE}."
                ),
            )

        valid_ns = _chunk_ns(chunks)
        real = [n for n in cited if n in valid_ns]
        if not real:
            return EvalResult(
                status="retry",
                feedback=(
                    "Citations must use [n] values from evidence_chunks. "
                    f"{Policy.GROUNDING_RULE}."
                ),
            )
        unknown = sorted({n for n in cited if n not in valid_ns})
        if unknown:
            return EvalResult(
                status="retry",
                feedback=(
                    f"Citation(s) {unknown} are not in evidence_chunks. "
                    f"{Policy.GROUNDING_RULE}."
                ),
            )

        extra = [
            url for url in _URL_RE.findall(markdown) if not _is_arxiv_url(url)
        ]
        if extra:
            return EvalResult(
                status="retry",
                feedback=(
                    "Extra HTTP sources are not allowed; only arxiv.org URLs. "
                    f"Found: {extra[0]}"
                ),
            )

        return EvalResult(
            status="pass",
            feedback="Deterministic grounding passed: real [n] citations and no extra sources.",
        )

    async def _judge_language_and_tone(
        self, data: dict, markdown: str
    ) -> EvalResult | None:
        if self._judge is None:
            return None
        query = str(data.get("query") or "")
        try:
            result = await self._judge.ainvoke(
                [
                    (
                        "system",
                        "You evaluate a student research answer. "
                        "Return status pass, retry, or fail with feedback.\n"
                        f"{_writer_checklist()}",
                    ),
                    (
                        "human",
                        f"Student query:\n{query}\n\nWriter markdown:\n{markdown}",
                    ),
                ]
            )
        except Exception:
            return None
        if isinstance(result, EvalResult):
            return result
        try:
            return EvalResult.model_validate(result)
        except Exception:
            return None
