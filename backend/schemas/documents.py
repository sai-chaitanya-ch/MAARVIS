from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int = 0
    chunks: int = 0
    status: str


class DocumentQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    document_ids: List[str] = Field(default_factory=list)
    conversation_id: Optional[str] = None
