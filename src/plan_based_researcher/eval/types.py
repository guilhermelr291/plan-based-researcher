from typing import Literal

from pydantic import BaseModel


class EvalResult(BaseModel):
    status: Literal["pass", "retry", "fail"]
    feedback: str
    plan_inadequate: bool = False


class PaperKey(BaseModel):
    arxiv_id: str
    version: str = ""


class SearchStepVerdict(BaseModel):
    step_index: int
    passed: bool
    plan_inadequate: bool = False
    feedback: str
    ranked_keys: list[PaperKey] = []


class SearchWaveJudgement(BaseModel):
    verdicts: list[SearchStepVerdict]
    reasoning: str
