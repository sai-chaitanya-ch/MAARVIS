from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JevCategory(str, Enum):
    CONVERSATIONAL = "CONVERSATIONAL"
    DIRECT_DETERMINISTIC = "DIRECT_DETERMINISTIC"
    QUANTITATIVE_MATH = "QUANTITATIVE_MATH"
    FACTUAL_RAG = "FACTUAL_RAG"
    CONFLICTING_SOURCES = "CONFLICTING_SOURCES"
    LOGICAL_PUZZLE = "LOGICAL_PUZZLE"
    CODE_AND_API = "CODE_AND_API"


class JevExecutionRoute(str, Enum):
    DIRECT_FAST = "DIRECT_FAST"
    DIRECT_SANDBOX = "DIRECT_SANDBOX"
    MULTI_AGENT = "MULTI_AGENT"
    MULTI_AGENT_RAG = "MULTI_AGENT_RAG"


class JevQuestion(BaseModel):
    type: str  # "choice", "score", or "noul"
    options: Optional[List[str]] = None
    min: Optional[int] = None
    max: Optional[int] = None


class JevRequest(BaseModel):
    model: str = "jev-latest"
    state: str
    questions: Dict[str, JevQuestion]


class JevResponse(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict)


class JevDecision(BaseModel):
    category: JevCategory
    route: JevExecutionRoute
    complexity: str = "standard"  # "low", "standard", "high"
    requires_rag: bool = False
    requires_verification: bool = False
    requires_code_execution: bool = False
    confidence: Optional[float] = None
    reasoning: str
    is_fallback: bool = False
    latency_ms: Optional[int] = None
