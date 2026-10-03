from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    VERIFICATION_INCOMPLETE = "verification_incomplete"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"
    ERROR = "error"
    DIRECT_ANSWER = "direct_answer"
    NOT_VERIFIED = "not_verified"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_lower = value.lower()
            for member in cls:
                if member.value == val_lower:
                    return member
            if val_lower in {"contradicted", "conflicted"}:
                return cls.CONFLICTING
            if val_lower in {"insufficient_evidence", "not_verified", "unverifiable"}:
                return cls.UNVERIFIED
            if val_lower in {"supported", "verified"}:
                return cls.VERIFIED
            if val_lower in {"partially_supported", "partial", "partially_verified"}:
                return cls.PARTIALLY_VERIFIED
            if val_lower in {"direct_answer", "direct", "not_applicable"}:
                return cls.DIRECT_ANSWER
        return None


class ClaimStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNVERIFIABLE = "UNVERIFIABLE"


class VerificationLevel(int, Enum):
    NONE = 0
    BASIC = 1
    MULTI_SOURCE = 2
    DEEP = 3


class GateDecision(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    REQUIRED = "REQUIRED"


class TaskType(str, Enum):
    CONVERSATION = "conversation"
    FACTUAL = "factual"
    CURRENT_INFO = "current_information"
    RESEARCH = "research"
    MATH = "math"
    CODE = "code"
    DOCUMENT = "document"
    REASONING = "reasoning"
    COMPARISON = "comparison"
    SUMMARIZATION = "summarization"
    VERIFICATION = "verification"
    MULTI_STEP = "multi_step"


class SourceType(str, Enum):
    WEB = "web"
    DOCUMENT = "document"
    CALCULATION = "calculation"
    CODE_EXECUTION = "code_execution"
    TOOL = "tool"


class VerificationSummary(BaseModel):
    model_config = {"populate_by_name": True, "extra": "allow"}

    performed: bool = False
    status: Optional[VerificationStatus] = None
    independent_verification_completed: bool = False
    independentVerificationCompleted: Optional[bool] = None

    total_claims: int = 0
    totalClaims: Optional[int] = None
    verified_claims: int = 0
    verifiedClaims: Optional[int] = None
    partially_verified_claims: int = 0
    partiallyVerifiedClaims: Optional[int] = None
    unverified_claims: int = 0
    unverifiedClaims: Optional[int] = None
    conflicting_claims: int = 0
    conflictingClaims: Optional[int] = None

    metrics: Dict[str, Optional[int]] = Field(default_factory=dict)
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    verification_methods: List[str] = Field(default_factory=list)
    verificationMethods: Optional[List[str]] = None
    iterations: int = 1

    score: Optional[float] = None
    claims_checked: int = 0
    supported: int = 0
    partial: int = 0
    unverified: int = 0
    contradicted: int = 0
    note: Optional[str] = None
    level: Optional[int] = None
    error: Optional[str] = None

    claims_summary: Optional[Dict[str, int]] = None
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    verification_methods_map: Optional[Dict[str, bool]] = None
    self_correction: Optional[Dict[str, Any]] = None
    agent_trace: Optional[List[Dict[str, Any]]] = None
    latency_ms: Optional[int] = None


class Source(BaseModel):
    id: str
    title: str
    url: Optional[str] = None
    domain: Optional[str] = None
    source_type: SourceType = SourceType.WEB
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    relevance: Optional[float] = None
    evidence: Optional[str] = None
    published_at: Optional[str] = None
    tier: Optional[int] = None


class ClaimResult(BaseModel):
    claim_id: str
    claim_text: str
    status: ClaimStatus
    confidence: Optional[float] = None
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str = ""
    importance: str = "medium"


class AgentEvent(BaseModel):
    event: str
    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[int] = None
    detail: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=32000)
    conversation_id: Optional[str] = None
    document_ids: List[str] = Field(default_factory=list)
    web_enabled: Optional[bool] = None
    code: Optional[str] = None
    language: Optional[str] = None
    mode: str = "AUTO"  # AUTO | MULTI_AGENT | DIRECT


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    verification: VerificationSummary
    sources: List[Source] = Field(default_factory=list)
    events: List[AgentEvent] = Field(default_factory=list)
    claims: List[ClaimResult] = Field(default_factory=list)
    routing: Optional[Dict[str, Any]] = None
    execution_id: Optional[str] = None
    execution_trace: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime
    message_count: int = 0


class ConversationDetail(BaseModel):
    id: str
    title: str
    messages: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
