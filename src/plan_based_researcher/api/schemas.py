from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str
    thread_id: str = Field(min_length=1)


class Citation(BaseModel):
    n: int
    arxiv_id: str
    title: str
    year: int
    url: str
    excerpt: str
    chunk_id: str


class AnswerCompleteData(BaseModel):
    markdown: str
    citations: list[Citation]


class PlanStep(BaseModel):
    agent: str  # REGISTRY key; validated later after parse, not here
    task: str
    reasoning: str
    historical: bool = False


class ResearchPlan(BaseModel):
    steps: list[PlanStep]


class GateDecision(BaseModel):
    in_domain: bool
    language: str
    reason: str
