from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MarvisMode(str, Enum):
    AUTO = "AUTO"
    MULTI_AGENT = "MULTI_AGENT"
    DIRECT = "DIRECT"


class MarvisRoute(str, Enum):
    DIRECT_FAST = "DIRECT_FAST"
    DIRECT_SANDBOX = "DIRECT_SANDBOX"
    MULTI_AGENT = "MULTI_AGENT"
    MULTI_AGENT_RAG = "MULTI_AGENT_RAG"


class JevCategory(str, Enum):
    CONVERSATIONAL = "CONVERSATIONAL"
    DIRECT_DETERMINISTIC = "DIRECT_DETERMINISTIC"
    QUANTITATIVE_MATH = "QUANTITATIVE_MATH"
    FACTUAL_RAG = "FACTUAL_RAG"
    CONFLICTING_SOURCES = "CONFLICTING_SOURCES"
    LOGICAL_PUZZLE = "LOGICAL_PUZZLE"
    CODE_AND_API = "CODE_AND_API"


class RoutingEngine(str, Enum):
    STAGE1_ATTACHMENT = "STAGE1_ATTACHMENT"
    STAGE1_USER_OVERRIDE = "STAGE1_USER_OVERRIDE"
    STAGE2_GREETING = "STAGE2_GREETING"
    STAGE2_AST = "STAGE2_AST"
    STAGE3_JEV = "STAGE3_JEV"
    STAGE3_FALLBACK = "STAGE3_FALLBACK"


class AgentStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AgentRunRecord(BaseModel):
    agent_id: str
    agent_name: str
    role: str
    status: AgentStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    latency_ms: Optional[int] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    model: Optional[str] = None
    gateway: Optional[str] = None
    tokens: Optional[int] = None
    evidence_refs: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class EvidenceChunk(BaseModel):
    chunk_id: str
    page: Optional[int] = None
    similarity: Optional[float] = None
    text: str
    source: Optional[str] = None


class EvidenceClaim(BaseModel):
    claim_id: str
    text: str
    status: str
    page: Optional[int] = None
    source: Optional[str] = None
    evidence_text: Optional[str] = None
    confidence: Optional[float] = None


class ExecutionEvidence(BaseModel):
    documents_used: int = 0
    claims_evaluated: int = 0
    claims_supported: int = 0
    relevant_chunks: List[EvidenceChunk] = Field(default_factory=list)
    claims: List[EvidenceClaim] = Field(default_factory=list)


class ExecutionTrace(BaseModel):
    execution_id: str
    user_query: str
    mode: MarvisMode
    route: MarvisRoute
    routing_engine: RoutingEngine
    jev_decision: Optional[Dict[str, Any]] = None
    agents: List[AgentRunRecord] = Field(default_factory=list)
    evidence: ExecutionEvidence = Field(default_factory=ExecutionEvidence)
    status: str  # VERIFIED, PARTIALLY_VERIFIED, INSUFFICIENT_EVIDENCE, UNVERIFIED, FAILED, DIRECT_ANSWER
    total_latency_ms: int = 0
    started_at: str
    completed_at: str
    capabilities: Optional[Dict[str, Any]] = None
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)


class RequiredCapabilities(BaseModel):
    basic_llm: bool = True
    rag: bool = False
    web_search: bool = False
    code_execution: bool = False
    multi_agent_reasoning: bool = False
    verification: bool = False
    jev: bool = False


class TriageDecision(BaseModel):
    selected_mode: MarvisMode
    active_route: MarvisRoute
    category: Optional[JevCategory] = None
    reasoning: str
    confidence: Optional[float] = None  # Only set if JEV provides calibrated probability
    requires_sandbox: bool = False
    requires_rag: bool = False
    escalated_by_attachment: bool = False
    routing_engine: RoutingEngine
    jev_raw: Optional[Dict[str, Any]] = None
    required_capabilities: Optional[RequiredCapabilities] = None
