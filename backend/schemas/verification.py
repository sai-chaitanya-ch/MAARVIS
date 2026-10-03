from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.chat import ClaimResult, Source, VerificationSummary


class VerifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=32000)
    question: Optional[str] = None


class VerifyResponse(BaseModel):
    verification: VerificationSummary
    claims: List[ClaimResult] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    answer: str = ""
