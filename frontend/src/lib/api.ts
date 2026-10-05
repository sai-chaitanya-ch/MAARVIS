export type VerificationStatus =
  | "verified"
  | "partially_verified"
  | "verification_incomplete"
  | "unverified"
  | "conflicting"
  | "error"
  | "VERIFIED"
  | "PARTIALLY_VERIFIED"
  | "INSUFFICIENT_EVIDENCE"
  | "CONTRADICTED"
  | "NOT_VERIFIED";

export interface EvidenceMetricsData {
  verified?: number | null;
  partiallyVerified?: number | null;
  unverified?: number | null;
  conflicting?: number | null;
}

export interface Verification {
  performed: boolean;
  independentVerificationCompleted?: boolean;
  independent_verification_completed?: boolean;
  status?: VerificationStatus | string;
  score?: number | null;
  totalClaims?: number;
  total_claims?: number;
  verifiedClaims?: number;
  verified_claims?: number;
  partiallyVerifiedClaims?: number;
  partially_verified_claims?: number;
  unverifiedClaims?: number;
  unverified_claims?: number;
  conflictingClaims?: number;
  conflicting_claims?: number;
  metrics?: EvidenceMetricsData;
  claims_checked?: number;
  supported?: number;
  partial?: number;
  unverified?: number;
  contradicted?: number;
  note?: string | null;
  level?: number | null;
  verificationMethods?: string[];
  verification_methods?: string[];
  verification_methods_map?: {
    evidence_retrieval?: boolean;
    claim_extraction?: boolean;
    independent?: boolean;
    contradiction_check?: boolean;
    critic?: boolean;
    correction?: boolean;
    reverification?: boolean;
  };
  claims_summary?: {
    total: number;
    verified: number;
    partial: number;
    unsupported: number;
    conflicting: number;
  };
  claims?: any[];
  decision?: string;
  decision_reason?: string;
  self_correction?: {
    required: boolean;
    initial_status?: string;
    problem?: string | null;
    correction?: string | null;
    reverification?: string | null;
    iterations?: number;
  };
  agent_trace?: {
    agent: string;
    status: string;
    duration_ms?: number;
  }[];
  iterations?: number;
  latency_ms?: number;
  error?: string | null;
}

export interface Source {
  id: string;
  title: string;
  url?: string | null;
  domain?: string | null;
  source_type?: string;
  evidence?: string | null;
  published_at?: string | null;
  relevance?: number | null;
  tier?: number | null;
  [key: string]: any;
}

export interface ClaimResult {
  claim_id: string;
  claim_text: string;
  status: string;
  confidence?: number | null;
  reason?: string;
  evidence_ids?: string[];
}

export interface AgentEvent {
  event: string;
  status: string;
  timestamp?: string;
  duration_ms?: number | null;
  detail?: string | null;
}

export interface AgentRunRecord {
  agent_id: string;
  agent_name: string;
  role: string;
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "SKIPPED";
  started_at?: string | null;
  completed_at?: string | null;
  latency_ms?: number | null;
  input_summary?: string | null;
  output_summary?: string | null;
  model?: string | null;
  gateway?: string | null;
  tokens?: number | null;
  evidence_refs?: string[];
  error?: string | null;
}

export interface EvidenceChunk {
  chunk_id: string;
  document_id?: string;
  page?: number | null;
  similarity?: number | null;
  text: string;
  source?: string | null;
}

export interface EvidenceClaim {
  claim_id: string;
  text: string;
  status: string;
  page?: number | null;
  source?: string | null;
  evidence_text?: string | null;
  confidence?: number | null;
}

export interface ExecutionEvidence {
  documents_used: number;
  claims_evaluated: number;
  claims_supported: number;
  relevant_chunks: EvidenceChunk[];
  claims: EvidenceClaim[];
}

export interface SystemCapability {
  connected: boolean;
  required: boolean;
  model?: string;
  label: string;
  description: string;
  key_masked?: string | null;
}

export interface SystemCapabilities {
  gemini: SystemCapability;
  rag: SystemCapability;
  jev: SystemCapability;
  web_search: SystemCapability;
  sandbox: SystemCapability;
  [key: string]: SystemCapability;
}

export interface Recommendation {
  provider: string;
  name: string;
  reason: string;
  action_label?: string;
  category?: string;
}

export interface ExecutionTrace {
  execution_id: string;
  user_query: string;
  mode: string;
  route: string;
  routing_engine: string;
  jev_decision?: {
    category?: string | null;
    confidence?: number | null;
    complexity?: string;
    requires_rag?: boolean;
    requires_sandbox?: boolean;
    reasoning?: string;
    reason?: string;
  };
  agents: AgentRunRecord[];
  evidence: ExecutionEvidence;
  status: string;
  total_latency_ms: number;
  started_at?: string;
  completed_at?: string;
  capabilities?: SystemCapabilities;
  recommendations?: Recommendation[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  verification?: Verification;
  sources?: Source[];
  events?: AgentEvent[];
  claims?: ClaimResult[];
  execution_id?: string;
  execution_trace?: ExecutionTrace;
  capabilities?: SystemCapabilities;
  recommendations?: Recommendation[];
  routing?: {
    mode: string;
    route: string;
    category: string | null;
    engine: string;
    confidence: number | null;
    requires_rag: boolean;
    requires_sandbox: boolean;
    attachment_escalated: boolean;
  };
}

export interface StreamEvent {
  type: string;
  [key: string]: unknown;
}

import { getAuthToken } from "./supabase";

export const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export const API = `${BASE_URL}/api`;

export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const token = await getAuthToken();
  const headers = new Headers(init.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(input, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("maarvis:unauthorized"));
    }
  }

  return response;
}

export async function getAuthHeaders(extraHeaders: Record<string, string> = {}): Promise<Record<string, string>> {
  const headers: Record<string, string> = { ...extraHeaders };
  try {
    const token = await getAuthToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  } catch {
    // ignore
  }
  return headers;
}

export async function fetchCapabilities(): Promise<SystemCapabilities> {
  const response = await authenticatedFetch(`${API}/providers/capabilities`);
  if (!response.ok) throw new Error("Failed to fetch system capabilities");
  return response.json();
}

export async function fetchHealth() {
  const response = await fetch(`${API}/health`);
  if (!response.ok) throw new Error("Health check failed");
  return response.json();
}

export async function fetchConversations() {
  const response = await authenticatedFetch(`${API}/conversations`);
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Authentication required. Provide a valid Supabase Bearer token in Authorization header.");
    }
    throw new Error("Could not load conversations");
  }
  return response.json();
}

export async function fetchConversation(id: string) {
  const response = await authenticatedFetch(`${API}/conversations/${id}`);
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Authentication required. Provide a valid Supabase Bearer token in Authorization header.");
    }
    throw new Error("Conversation not found");
  }
  return response.json();
}

export async function createConversation(title?: string): Promise<{ id: string }> {
  const response = await authenticatedFetch(`${API}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title || "New Conversation" }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Could not create conversation" }));
    throw new Error(err.detail || "Could not create conversation");
  }
  return response.json();
}

export async function deleteConversation(id: string): Promise<{ ok: boolean }> {
  const response = await authenticatedFetch(`${API}/conversations/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Could not delete conversation");
  return response.json();
}

export interface DocumentItem {
  id: string;
  filename: string;
  path: string;
  chunks: number;
  created_at: string;
  pages?: number;
}

export interface DocumentPassage {
  id?: string;
  chunk_id?: string;
  document_id?: string;
  page?: number;
  section?: string | null;
  text: string;
  source?: string;
  score?: number;
  rerank_score?: number;
}

export interface RAGChatResponse {
  answer: string;
  sources: Source[];
  passages: DocumentPassage[];
  verification: Verification;
  claims: ClaimResult[];
}

export async function fetchDocuments(): Promise<DocumentItem[]> {
  const response = await authenticatedFetch(`${API}/documents`);
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Authentication required. Provide a valid Supabase Bearer token in Authorization header.");
    }
    throw new Error("Could not load documents");
  }
  return response.json();
}

export async function deleteDocument(documentId: string): Promise<{ status: string; document_id: string }> {
  const response = await authenticatedFetch(`${API}/documents/${documentId}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Could not delete document");
  return response.json();
}

export async function uploadDocument(file: File): Promise<{
  document_id: string;
  filename: string;
  pages: number;
  chunks: number;
  status: string;
}> {
  const data = new FormData();
  data.append("file", file);
  // Do NOT pass Content-Type header so the browser sets multipart/form-data boundary automatically
  const response = await authenticatedFetch(`${API}/documents/upload`, {
    method: "POST",
    body: data,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return response.json();
}

export async function chatWithDocuments(payload: {
  message: string;
  document_ids?: string[];
}): Promise<RAGChatResponse> {
  const response = await authenticatedFetch(`${API}/documents/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "RAG query failed" }));
    throw new Error(err.detail || "RAG query failed");
  }
  return response.json();
}

export async function streamChat(
  payload: {
    message: string;
    conversation_id?: string | null;
    document_ids?: string[];
    web_enabled?: boolean | null;
    mode?: string;
  },
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
) {
  const response = await authenticatedFetch(`${API}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok || !response.body) {
    const err = await response.json().catch(() => ({ detail: "Chat failed" }));
    throw new Error(err.detail || "Chat failed");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      onEvent(JSON.parse(json) as StreamEvent);
    }
  }
}

// ---------------------------------------------------------------------
// Evaluation & Verification Laboratory Interfaces & API Functions
// ---------------------------------------------------------------------

export interface EvaluationCase {
  id: string;
  category: string;
  title: string;
  input: string;
  expected_decision?: string;
  expected_verification?: string;
}

export interface PipelineStage {
  id: string;
  name: string;
  agent: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped" | "rejected";
  durationMs: number;
  desc: string;
}

export interface ClaimVerificationItem {
  id: string;
  claimText: string;
  status: "verified" | "partially_verified" | "unverified" | "conflicting";
  verifier?: string;
  verificationMethod?: string;
  evidenceStrength?: string;
  reason?: string;
  evidence?: {
    sourceId: string;
    title: string;
    url?: string | null;
    tier?: number;
    snippet?: string;
  }[];
}

export interface ProvenanceEvidence {
  id: string;
  claimId: string;
  title: string;
  domain?: string | null;
  url?: string | null;
  sourceType: string;
  tier: number;
  retrievalTimeMs: number;
  evidenceStrength: string;
  snippet: string;
}

export interface ContradictionItem {
  claim: string;
  sourceA: string;
  sourceB: string;
  conflictType: string;
  resolution: string;
}

export interface CriticIssue {
  id: number;
  type: string;
  description: string;
  severity: string;
}

export interface RevisionRecord {
  revision: number;
  label: string;
  answer: string;
  issue?: string | null;
  passed: boolean;
}

export interface SandboxInfo {
  type: "math" | "code" | "api" | "none";
  input: string;
  code?: string;
  output: string;
  runtimeMs: number;
  status: string;
  testCases?: { test: string; expected?: string; passed: boolean }[];
  passedTests: number;
  failedTests: number;
}

export interface AgentTraceItem {
  name: string;
  role: string;
  status: string;
  durationMs: number;
  input: string;
  output: string;
}

export interface AuditEventItem {
  time: string;
  agent: string;
  action: string;
  status: string;
  detail: string;
}

export interface SystemBenchmarksData {
  testCases: number;
  claimsEvaluated: number;
  metrics: {
    claimVerificationAccuracy: number;
    unsupportedClaimDetection: number;
    contradictionDetection: number;
    evidencePrecision: number;
    selfCorrectionSuccess: number;
    falseAcceptanceRate: number;
    falseRejectionRate: number;
    averageVerificationIterations: number;
  };
  breakdownByCategory: {
    category: string;
    tests: number;
    accuracy: number;
    status: string;
  }[];
}

export interface VerificationRun {
  id: string;
  taskId: string;
  caseId?: string;
  caseTitle?: string;
  query: string;
  finalAnswer: string;
  status: string;
  decision: "ACCEPT" | "PARTIALLY_ACCEPT" | "REJECT" | "INSUFFICIENT_EVIDENCE" | "CONFLICTING_EVIDENCE" | "UNSAFE";
  decisionReason: string;
  evidenceScore: number;
  latency: number;
  verificationIterations: number;
  risk: "LOW" | "MEDIUM" | "HIGH";
  pipeline: PipelineStage[];
  claims: ClaimVerificationItem[];
  evidence: ProvenanceEvidence[];
  contradictions: {
    hasConflict: boolean;
    conflicts: ContradictionItem[];
  };
  critic: {
    claimsReviewed: number;
    issuesCount: number;
    risk: string;
    issues: CriticIssue[];
  };
  sandbox: SandboxInfo;
  revisions: RevisionRecord[];
  correctionCount: number;
  reVerificationAttempts: number;
  agents: AgentTraceItem[];
  auditTrail: AuditEventItem[];
  metrics: {
    verified: number;
    partiallyVerified: number;
    unverified: number;
    conflicting: number;
    claimsEvaluated: number;
    claimsSupported: number;
    claimsPartiallySupported: number;
    unsupportedClaims: number;
    conflictingClaims: number;
    sourcesUsed: number;
    independentChecks: number;
    verificationIterations: number;
    correctionAttempts: number;
  };
  createdAt: string;
  completedAt: string;
}

export async function fetchEvaluationCases(): Promise<{ total: number; cases: EvaluationCase[] }> {
  const response = await authenticatedFetch(`${API}/evaluation/cases`);
  if (!response.ok) throw new Error("Failed to fetch evaluation test cases");
  return response.json();
}

export async function fetchEvaluationBenchmarks(): Promise<SystemBenchmarksData> {
  const response = await authenticatedFetch(`${API}/evaluation/benchmarks`);
  if (!response.ok) throw new Error("Failed to fetch evaluation benchmarks");
  return response.json();
}

export async function fetchLatestEvaluationRun(): Promise<VerificationRun> {
  const response = await authenticatedFetch(`${API}/evaluation/latest`);
  if (!response.ok) throw new Error("Failed to fetch latest verification run");
  return response.json();
}

export async function executeEvaluationRun(payload: { case_id?: string; query?: string }): Promise<VerificationRun> {
  const response = await authenticatedFetch(`${API}/evaluation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Evaluation execution failed" }));
    throw new Error(err.detail || "Evaluation execution failed");
  }
  return response.json();
}

// ---------------------------------------------------------------------
// Provider Credential Management API
// ---------------------------------------------------------------------

export interface StoredProvider {
  id: string;
  provider: string;
  label: string;
  model: string;
  key_masked: string;
  status: "connected" | "failed" | "unchecked";
  is_active?: number;
  last_tested_at?: string;
  created_at: string;
}

export interface SupportedProviderInfo {
  id: string;
  name: string;
  models: string[];
}

export async function fetchSupportedProviders(): Promise<SupportedProviderInfo[]> {
  const r = await authenticatedFetch(`${API}/providers/supported`);
  if (!r.ok) return [];
  const d = await r.json();
  return d.providers || [];
}

export async function fetchProviders(): Promise<StoredProvider[]> {
  const r = await authenticatedFetch(`${API}/providers`);
  if (!r.ok) return [];
  const d = await r.json();
  return d.providers || [];
}

export async function saveProviderCredential(data: {
  provider: string;
  api_key: string;
  model?: string;
  label?: string;
}): Promise<StoredProvider> {
  const r = await authenticatedFetch(`${API}/providers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: "Failed to save provider" }));
    throw new Error(err.detail || "Failed to save provider");
  }
  return r.json();
}

export async function updateProviderCredential(
  id: string,
  data: { api_key?: string; model?: string; label?: string }
): Promise<StoredProvider> {
  const r = await authenticatedFetch(`${API}/providers/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: "Failed to update provider" }));
    throw new Error(err.detail || "Failed to update provider");
  }
  return r.json();
}

export async function testProviderCredential(id: string): Promise<{ success: boolean; provider?: string; error?: string }> {
  const r = await authenticatedFetch(`${API}/providers/${id}/test`, { method: "POST" });
  return r.json();
}

export async function activateProviderCredential(id: string): Promise<{ ok: boolean }> {
  const r = await authenticatedFetch(`${API}/providers/${id}/activate`, { method: "POST" });
  return r.json();
}

export async function deleteProviderCredential(id: string): Promise<{ ok: boolean }> {
  const r = await authenticatedFetch(`${API}/providers/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Failed to delete provider");
  return r.json();
}

