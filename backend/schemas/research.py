from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.chat import Source, VerificationSummary


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None


class ResearchResponse(BaseModel):
    query: str
    answer: str
    sources: List[Source] = Field(default_factory=list)
    verification: VerificationSummary
