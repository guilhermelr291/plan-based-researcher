from typing import Literal

from pydantic import BaseModel


class EvalResult(BaseModel):
    status: Literal["pass", "retry", "fail"]
    feedback: str
