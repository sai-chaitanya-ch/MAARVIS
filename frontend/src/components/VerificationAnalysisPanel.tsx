import { useState } from "react";
import {
  X,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ShieldCheck,
  ShieldOff,
  Cpu,
  FileText,
  Activity,
  Layers,
  Database,
  Search,
  Code,
  Terminal,
  BrainCircuit,
  Sparkles,
  Globe,
  Bot,
} from "lucide-react";
import AgentWorkflowGraph from "./AgentWorkflowGraph";
import {
  Verification,
  Source,
  ClaimResult,
  ExecutionTrace,
  AgentRunRecord,
  SystemCapabilities,
  Recommendation,
} from "../lib/api";

interface VerificationAnalysisPanelProps {
  verification?: Verification;
  sources?: Source[];
  claims?: ClaimResult[];
  executionTrace?: ExecutionTrace;
  executionId?: string;
  capabilities?: SystemCapabilities;
  recommendations?: Recommendation[];
  onOpenSettings?: (tab?: string) => void;
  onClose: () => void;
}

type TabKey = "overview" | "evidence" | "agents";

export default function VerificationAnalysisPanel({
  verification,
  sources = [],
  claims = [],
  executionTrace: propTrace,
  executionId: propExecId,
  capabilities: propCapabilities,
  recommendations: propRecommendations,
  onOpenSettings,
  onClose,
}: VerificationAnalysisPanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.has("agents")) return "agents";
      if (params.has("evidence")) return "evidence";
    }
    return "overview";
  });
  const [expandedClaims, setExpandedClaims] = useState<Record<string, boolean>>({});
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [agentViewMode, setAgentViewMode] = useState<"graph" | "list">("graph");

  const toggleClaim = (id: string) => {
    setExpandedClaims((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Resolve execution trace from props or verification object
  const executionTrace: ExecutionTrace | undefined =
    propTrace || (verification as any)?.execution_trace;
  const executionId: string =
    propExecId || (verification as any)?.execution_id || executionTrace?.execution_id || "exec_live";

  // ── Real claim data only ────────────────────────────────────────────────
  const displayClaims: any[] =
    executionTrace?.evidence?.claims && executionTrace.evidence.claims.length > 0
      ? executionTrace.evidence.claims
      : verification?.claims && verification.claims.length > 0
      ? verification.claims
      : claims && claims.length > 0
      ? claims
      : [];

  // ── Real sources only ──
  const displaySources: Source[] = (sources ?? []).filter(
    (s: any) => s.source_role !== "verification_evidence"
  );

  // ── Math detection ──────────────────────────────────────────────────────
  const isMath = Boolean(
    (verification as any)?.is_math === true ||
    (verification as any)?.is_math === "true" ||
    verification?.note?.toLowerCase().includes("deterministic")
  );

  const rawStatus = String(verification?.status || "").toLowerCase();
  const decisionLabel = String(verification?.decision || "").toUpperCase();

  const isDirect =
    rawStatus === "direct_answer" ||
    decisionLabel === "DIRECT ANSWER" ||
    (verification?.performed === false && !isMath) ||
    (displayClaims.length === 0 && displaySources.length === 0 && !isMath);

  // ── Real percentages from backend ───────────────────────────────────────
  const metrics = verification?.metrics;
  const vPct: number = isMath
    ? 100
    : isDirect
    ? 0
    : typeof metrics?.verified === "number"
    ? Math.round(metrics.verified)
    : 0;
  const pPct: number = isMath || isDirect
    ? 0
    : typeof metrics?.partiallyVerified === "number"
    ? Math.round(metrics.partiallyVerified)
    : 0;
  const cPct: number = isMath || isDirect
    ? 0
    : typeof metrics?.conflicting === "number"
    ? Math.round(metrics.conflicting)
    : 0;
  const uPct: number = isDirect ? 0 : Math.max(0, 100 - vPct - pPct - cPct);

  // ── Real claim counts ───────────────────────────────────────────────────
  const totalClaims = isDirect
    ? 0
    : (executionTrace?.evidence?.claims_evaluated ??
       verification?.totalClaims ??
       verification?.total_claims ??
       displayClaims.length);
  const supCount = isMath
    ? 1
    : isDirect
    ? 0
    : (executionTrace?.evidence?.claims_supported ??
       verification?.verifiedClaims ??
       verification?.verified_claims ??
       0);
  const partCount = isDirect
    ? 0
    : (verification?.partiallyVerifiedClaims ?? verification?.partially_verified_claims ?? 0);
  const confCount = isDirect
    ? 0
    : (verification?.conflictingClaims ?? verification?.conflicting_claims ?? 0);
  const unsupCount = isDirect
    ? 0
    : Math.max(0, totalClaims - (supCount + partCount + confCount));

  // ── Status badge driven by real backend status ──────────────────────────
  let statusBadge: { label: string; badgeClass: string; icon: React.ReactNode };
  if (isDirect || decisionLabel === "DIRECT ANSWER") {
    statusBadge = {
      label: "DIRECT ANSWER",
      icon: <CheckCircle2 size={14} className="text-neutral-500" />,
      badgeClass: "bg-neutral-100 text-neutral-700 border-neutral-200",
    };
  } else if (isMath || decisionLabel === "SANDBOX VERIFIED") {
    statusBadge = {
      label: "SANDBOX VERIFIED",
      icon: <CheckCircle2 size={14} className="text-emerald-600" />,
      badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200",
    };
  } else if (decisionLabel === "MULTI-SOURCE VERIFIED") {
    statusBadge = {
      label: "MULTI-SOURCE VERIFIED",
      icon: <CheckCircle2 size={14} className="text-emerald-600" />,
      badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200",
    };
  } else if (decisionLabel === "SUPPORTED BY DOCUMENT") {
    statusBadge = {
      label: "SUPPORTED BY DOCUMENT",
      icon: <CheckCircle2 size={14} className="text-blue-600" />,
      badgeClass: "bg-blue-50 text-blue-700 border-blue-200",
    };
  } else if (decisionLabel === "SUPPORTED BY EXTERNAL SOURCES") {
    statusBadge = {
      label: "SUPPORTED BY EXTERNAL SOURCES",
      icon: <CheckCircle2 size={14} className="text-cyan-600" />,
      badgeClass: "bg-cyan-50 text-cyan-700 border-cyan-200",
    };
  } else if (decisionLabel === "VERIFIED" || rawStatus === "verified") {
    statusBadge = {
      label: "VERIFIED",
      icon: <CheckCircle2 size={14} className="text-emerald-600" />,
      badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200",
    };
  } else if (rawStatus === "conflicting" || decisionLabel === "CONFLICTING") {
    statusBadge = {
      label: "CONFLICTING",
      icon: <AlertTriangle size={14} className="text-orange-600" />,
      badgeClass: "bg-orange-50 text-orange-700 border-orange-200",
    };
  } else if (rawStatus === "partially_verified" || rawStatus === "partial" || decisionLabel === "PARTIALLY VERIFIED") {
    statusBadge = {
      label: "PARTIALLY VERIFIED",
      icon: <span className="text-amber-600 font-bold text-xs">◐</span>,
      badgeClass: "bg-amber-50 text-amber-700 border-amber-200",
    };
  } else {
    statusBadge = {
      label: "NOT VERIFIED",
      icon: <ShieldOff size={14} className="text-neutral-500" />,
      badgeClass: "bg-neutral-100 text-neutral-600 border-neutral-200",
    };
  }

  // ── SVG Donut ───────────────────────────────────────────────────────────
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeWidth = 9;
  const center = 48;
  const vDash = (vPct / 100) * circumference;
  const pDash = (pPct / 100) * circumference;
  const uDash = (uPct / 100) * circumference;
  const cDash = (cPct / 100) * circumference;

  // ── Real agents list from backend execution trace ───────────────────────
  const agents: AgentRunRecord[] = executionTrace?.agents ?? [];
  const selectedAgent = agents.find((a) => a.agent_id === selectedAgentId) || agents[0];

  // ── Real evidence chunks from Supabase pgvector ────────────────────────
  const relevantChunks = executionTrace?.evidence?.relevant_chunks ?? [];

  // Capabilities and Recommendations resolution
  const activeCapabilities =
    propCapabilities ||
    executionTrace?.capabilities ||
    (verification as any)?.capabilities;
  const activeRecommendations =
    propRecommendations ||
    executionTrace?.recommendations ||
    (verification as any)?.recommendations ||
    [];

  const hasDocEvidence =
    relevantChunks.length > 0 || displaySources.some((s) => s.source_type === "document");
  const hasWebEvidence = displaySources.some(
    (s) => s.source_type !== "document" && Boolean(s.url)
  );
  const jevActive = Boolean(
    executionTrace?.routing_engine === "STAGE3_JEV" ||
    (executionTrace?.jev_decision && executionTrace.jev_decision.category) ||
    activeCapabilities?.jev?.connected
  );
  const webActive = Boolean(hasWebEvidence || activeCapabilities?.web_search?.connected);

  // Helper icons for agents
  const getAgentIcon = (id: string) => {
    switch (id) {
      case "jev_decision":
        return <BrainCircuit size={14} className="text-purple-600" />;
      case "marvis_router":
        return <Layers size={14} className="text-blue-600" />;
      case "rag_agent":
        return <Database size={14} className="text-emerald-600" />;
      case "researcher_agent":
        return <Search size={14} className="text-cyan-600" />;
      case "coder_agent":
        return <Code size={14} className="text-indigo-600" />;
      case "ast_sandbox":
        return <Terminal size={14} className="text-amber-600" />;
      case "fact_verifier":
        return <ShieldCheck size={14} className="text-emerald-600" />;
      case "synthesizer":
        return <Cpu size={14} className="text-neutral-800" />;
      default:
        return <Activity size={14} className="text-neutral-600" />;
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[460px] flex-col border-l border-[#E5E7EB] bg-white shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#F3F4F6] px-5 py-3">
        <div className="flex items-center gap-2">
          <ShieldCheck size={18} className="text-[#111111]" />
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-[#111111]">
              Verification Analysis
            </h2>
            <p className="text-[10px] text-neutral-400 font-mono">{executionId}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-7 w-7 items-center justify-center rounded-md text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
          title="Close panel"
        >
          <X size={16} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#E5E7EB] bg-[#F8F9FA] px-4">
        {[
          { key: "overview", label: "Overview", icon: <Layers size={13} /> },
          { key: "evidence", label: "Evidence", icon: <FileText size={13} />, count: displayClaims.length || relevantChunks.length || undefined },
          { key: "agents", label: "Agents", icon: <Cpu size={13} />, count: agents.filter(a => a.status === "COMPLETED").length || undefined },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setActiveTab(t.key as TabKey)}
            className={`flex items-center gap-1.5 py-2.5 px-3.5 text-xs font-medium border-b-2 transition cursor-pointer ${
              activeTab === t.key
                ? "border-[#111111] text-[#111111] font-semibold bg-white"
                : "border-transparent text-[#6B7280] hover:text-[#111111]"
            }`}
          >
            {t.icon}
            <span>{t.label}</span>
            {t.count !== undefined && (
              <span className="ml-1 rounded-full bg-neutral-200/80 px-1.5 py-0.2 text-[10px] font-semibold text-neutral-700">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Scrollable tab body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 text-[#111111] text-xs">
        {/* ================================================================ */}
        {/* TAB 1: OVERVIEW                                                 */}
        {/* ================================================================ */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            {/* Status Card */}
            <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-3.5 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-semibold text-[#6B7280] uppercase tracking-wider block mb-1">
                  Evaluation Verdict
                </span>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold ${statusBadge.badgeClass}`}
                >
                  {statusBadge.icon}
                  <span>{statusBadge.label}</span>
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-semibold text-[#6B7280] uppercase tracking-wider block mb-0.5">
                  Route
                </span>
                <span className="text-xs font-mono font-medium text-neutral-800">
                  {executionTrace?.route || (isDirect ? "DIRECT_FAST" : "MULTI_AGENT")}
                </span>
              </div>
            </div>

            {/* Evidence Metrics Donut (only if not a pure direct conversational query) */}
            {!isDirect && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-4">
                <span className="text-[10px] font-semibold text-[#111111] uppercase tracking-wider block mb-3">
                  Evidence Metrics
                </span>
                <div className="flex items-center justify-between gap-4">
                  <div className="relative shrink-0 flex items-center justify-center">
                    <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
                      <circle cx={center} cy={center} r={radius} fill="none" stroke="#F3F4F6" strokeWidth={strokeWidth} />
                      {vPct > 0 && (
                        <circle cx={center} cy={center} r={radius} fill="none" stroke="#10B981" strokeWidth={strokeWidth}
                          strokeDasharray={`${vDash} ${circumference}`} strokeDashoffset={0} strokeLinecap="round" />
                      )}
                      {pPct > 0 && (
                        <circle cx={center} cy={center} r={radius} fill="none" stroke="#F59E0B" strokeWidth={strokeWidth}
                          strokeDasharray={`${pDash} ${circumference}`} strokeDashoffset={-vDash} strokeLinecap="round" />
                      )}
                      {uPct > 0 && (
                        <circle cx={center} cy={center} r={radius} fill="none" stroke="#EF4444" strokeWidth={strokeWidth}
                          strokeDasharray={`${uDash} ${circumference}`} strokeDashoffset={-(vDash + pDash)} strokeLinecap="round" />
                      )}
                      {cPct > 0 && (
                        <circle cx={center} cy={center} r={radius} fill="none" stroke="#F97316" strokeWidth={strokeWidth}
                          strokeDasharray={`${cDash} ${circumference}`} strokeDashoffset={-(vDash + pDash + uDash)} strokeLinecap="round" />
                      )}
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
                      <span className="text-base font-bold text-[#111111] tracking-tight leading-none">{vPct}%</span>
                      <span className="text-[8.5px] font-medium text-[#6B7280] mt-0.5 leading-tight">
                        Evidence<br />Verified
                      </span>
                    </div>
                  </div>
                  <div className="flex-1 space-y-1.5 text-[11px]">
                    {[
                      { label: "Verified", pct: vPct, color: "#10B981" },
                      { label: "Partially Verified", pct: pPct, color: "#F59E0B" },
                      { label: "Unverified", pct: uPct, color: "#EF4444" },
                      { label: "Conflicting", pct: cPct, color: "#F97316" },
                    ].map(({ label, pct, color }) => (
                      <div key={label} className="flex items-center justify-between">
                        <span className="flex items-center gap-1.5 text-[#374151]">
                          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
                          {label}
                        </span>
                        <span className="font-semibold text-[#111111]">{pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Verification Summary Grid */}
            <div className="rounded-xl border border-[#E5E7EB] bg-white p-3.5">
              <span className="text-[10px] font-semibold text-[#111111] uppercase tracking-wider block mb-2">
                Verification Summary
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11.5px]">
                {[
                  { label: "Claims evaluated", value: totalClaims, color: "text-[#111111]" },
                  { label: "Supported", value: supCount, color: "text-emerald-600" },
                  { label: "Partially supported", value: partCount, color: "text-amber-600" },
                  { label: "Unsupported", value: unsupCount, color: "text-rose-600" },
                  { label: "Conflicting", value: confCount, color: "text-orange-600" },
                  { label: "Sources analyzed", value: displaySources.length, color: "text-[#111111]" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex items-center justify-between border-b border-[#F3F4F6] pb-1">
                    <span className="text-[#6B7280]">{label}</span>
                    <span className={`font-semibold ${color}`}>{value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Decision explanation */}
            <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-3.5">
              <span className="text-[10px] font-semibold text-[#111111] uppercase tracking-wider block mb-1">
                Decision Rationale
              </span>
              <p className="text-xs text-[#4B5563] leading-relaxed">
                {verification?.decision_reason ||
                  verification?.note ||
                  (isDirect
                    ? "Conversational query processed directly through the active AI provider without multi-agent verification."
                    : "Evaluated claims against retrieved evidence.")}
              </p>
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* TAB 2: EVIDENCE                                                 */}
        {/* ================================================================ */}
        {activeTab === "evidence" && (
          <div className="space-y-4">
            {/* Context-Aware Recommendations Banner */}
            {activeRecommendations && activeRecommendations.length > 0 && (
              <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-3.5 space-y-2">
                <div className="flex items-center gap-1.5 text-blue-900 font-semibold text-xs">
                  <Sparkles size={14} className="text-blue-600 shrink-0" />
                  <span>Recommendation for This Query</span>
                </div>
                {activeRecommendations.map((rec: Recommendation, i: number) => (
                  <div key={i} className="flex items-center justify-between gap-3 text-[11.5px] text-blue-800">
                    <p className="leading-snug">{rec.reason}</p>
                    {onOpenSettings && (
                      <button
                        onClick={() => onOpenSettings("providers")}
                        className="shrink-0 rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-blue-700 transition cursor-pointer shadow-2xs"
                      >
                        {rec.action_label || "Configure"}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Capabilities & Grounding Disclosure Card */}
            <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-3.5 space-y-2.5">
              <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-2">
                <span className="text-[10px] font-bold text-neutral-800 uppercase tracking-wider">
                  Capabilities &amp; Grounding Disclosure
                </span>
                <span className="text-[9.5px] text-neutral-400 font-mono">
                  Dependency Model
                </span>
              </div>
              <div className="space-y-2 text-[11.5px]">
                {/* Active AI Provider */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-1.5">
                    <span className="text-emerald-600 font-bold mt-0.5">✓</span>
                    <div>
                      <span className="font-semibold text-neutral-900">
                        {activeCapabilities?.ai_provider?.label || activeCapabilities?.gemini?.label || "Active AI Provider"}
                      </span>
                      <p className="text-[10.5px] text-neutral-500">
                        {activeCapabilities?.ai_provider?.model && activeCapabilities.ai_provider.model !== "None"
                          ? `Model: ${activeCapabilities.ai_provider.model} • Core reasoning & synthesis`
                          : "Core answer generation, reasoning & synthesis active"}
                      </p>
                    </div>
                  </div>
                  <span className="text-[9.5px] font-bold text-rose-600 bg-rose-50 px-1 py-0.2 rounded border border-rose-200">
                    REQUIRED
                  </span>
                </div>

                {/* Document RAG */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-1.5">
                    <span className={`font-bold mt-0.5 ${hasDocEvidence ? "text-emerald-600" : "text-neutral-400"}`}>
                      {hasDocEvidence ? "✓" : "○"}
                    </span>
                    <div>
                      <span className="font-semibold text-neutral-900">Document RAG (pgvector)</span>
                      <p className="text-[10.5px] text-neutral-500">
                        {hasDocEvidence
                          ? "Vector chunks retrieved and verified"
                          : "Available • Ready for document questions"}
                      </p>
                    </div>
                  </div>
                  <span className={`text-[9.5px] font-medium px-1 py-0.2 rounded border ${
                    hasDocEvidence ? "text-emerald-700 bg-emerald-50 border-emerald-200" : "text-neutral-500 bg-neutral-100 border-neutral-200"
                  }`}>
                    {hasDocEvidence ? "Active Grounding" : "Available"}
                  </span>
                </div>

                {/* JEV AI */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-1.5">
                    <span className={`font-bold mt-0.5 ${jevActive ? "text-purple-600" : "text-neutral-400"}`}>
                      {jevActive ? "✓" : "○"}
                    </span>
                    <div>
                      <span className="font-semibold text-neutral-900">JEV AI</span>
                      <p className="text-[10.5px] text-neutral-500">
                        {jevActive
                          ? "Semantic decision routing & triage active"
                          : "Not connected • Local deterministic fallback active"}
                      </p>
                    </div>
                  </div>
                  <span className="text-[9.5px] font-medium text-neutral-500 bg-neutral-100 px-1 py-0.2 rounded border border-neutral-200">
                    Optional
                  </span>
                </div>

                {/* Web Search */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-1.5">
                    <span className={`font-bold mt-0.5 ${webActive ? "text-cyan-600" : "text-neutral-400"}`}>
                      {webActive ? "✓" : "○"}
                    </span>
                    <div>
                      <span className="font-semibold text-neutral-900">Web Search</span>
                      <p className="text-[10.5px] text-neutral-500">
                        {webActive
                          ? "Live web retrieval & external evidence active"
                          : "Not connected • Independent web verification unavailable"}
                      </p>
                    </div>
                  </div>
                  <span className="text-[9.5px] font-medium text-neutral-500 bg-neutral-100 px-1 py-0.2 rounded border border-neutral-200">
                    Optional
                  </span>
                </div>
              </div>
            </div>

            {/* Header Metrics */}
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-2">
                <span className="text-[10px] text-neutral-500 uppercase block">Docs</span>
                <span className="text-sm font-bold text-neutral-900">
                  {executionTrace?.evidence?.documents_used ?? (relevantChunks.length > 0 ? 1 : 0)}
                </span>
              </div>
              <div className="rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-2">
                <span className="text-[10px] text-neutral-500 uppercase block">Claims</span>
                <span className="text-sm font-bold text-neutral-900">{totalClaims}</span>
              </div>
              <div className="rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-2">
                <span className="text-[10px] text-neutral-500 uppercase block">Supported</span>
                <span className="text-sm font-bold text-emerald-600">{supCount}</span>
              </div>
              <div className="rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-2">
                <span className="text-[10px] text-neutral-500 uppercase block">Chunks</span>
                <span className="text-sm font-bold text-blue-600">
                  {relevantChunks.length || displaySources.filter(s => s.source_type === "document").length}
                </span>
              </div>
            </div>

            {/* Claims Section */}
            <div>
              <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider block mb-2">
                Evaluated Claims ({displayClaims.length})
              </span>
              {displayClaims.length === 0 ? (
                <div className="rounded-lg border border-dashed border-[#E5E7EB] p-4 text-center text-xs text-neutral-400">
                  No discrete factual claims were extracted for this response.
                </div>
              ) : (
                <div className="space-y-2">
                  {displayClaims.map((claim, idx) => {
                    const cid = claim.claim_id || `c${idx + 1}`;
                    const isExpanded = Boolean(expandedClaims[cid]);
                    const st = String(claim.status || "").toUpperCase();
                    const isSup = st === "SUPPORTED" || st === "VERIFIED";
                    const isPart = st === "PARTIALLY_SUPPORTED" || st === "PARTIAL";
                    const isConf = st === "CONTRADICTED" || st === "CONFLICTING";
                    return (
                      <div key={cid} className="rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-2.5">
                        <button
                          type="button"
                          onClick={() => toggleClaim(cid)}
                          className="w-full text-left flex items-start justify-between gap-2 cursor-pointer"
                        >
                          <div className="flex items-start gap-2">
                            <span className="mt-0.5">
                              {isSup ? (
                                <CheckCircle2 size={13} className="text-emerald-600" />
                              ) : isPart ? (
                                <span className="text-amber-600 text-xs font-bold">◐</span>
                              ) : isConf ? (
                                <AlertTriangle size={13} className="text-orange-600" />
                              ) : (
                                <XCircle size={13} className="text-rose-600" />
                              )}
                            </span>
                            <div>
                              <div className="flex items-center gap-1.5 mb-0.5">
                                <span className="font-semibold text-[11px] text-[#111111]">
                                  Claim {String(idx + 1).padStart(2, "0")}
                                </span>
                                <span
                                  className={`text-[9.5px] px-1.5 py-0.2 rounded font-medium ${
                                    isSup
                                      ? "bg-emerald-50 text-emerald-700"
                                      : isPart
                                      ? "bg-amber-50 text-amber-700"
                                      : isConf
                                      ? "bg-orange-50 text-orange-700"
                                      : "bg-rose-50 text-rose-700"
                                  }`}
                                >
                                  {isSup ? "Supported" : isPart ? "Partially supported" : isConf ? "Conflicting" : "Unsupported"}
                                </span>
                                {claim.page && (
                                  <span className="text-[10px] text-neutral-400 font-mono">
                                    Page {claim.page}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-[#374151] line-clamp-2">
                                "{claim.text || claim.claim_text}"
                              </p>
                            </div>
                          </div>
                          <span className="text-[#9CA3AF] shrink-0 mt-1">
                            {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          </span>
                        </button>
                        {isExpanded && (
                          <div className="mt-2 pt-2 border-t border-[#E5E7EB] space-y-1 text-[11px] text-neutral-600">
                            {claim.source && (
                              <p><span className="font-medium text-neutral-700">Source:</span> {claim.source}</p>
                            )}
                            {(claim.evidence_text || claim.reason) && (
                              <p><span className="font-medium text-neutral-700">Evidence:</span> {claim.evidence_text || claim.reason}</p>
                            )}
                            {claim.confidence && (
                              <p><span className="font-medium text-neutral-700">Confidence:</span> {Math.round(claim.confidence * 100)}%</p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Document Chunks Section (pgvector) */}
            <div>
              <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider block mb-2">
                Retrieved Vector Chunks (pgvector)
              </span>
              {relevantChunks.length === 0 ? (
                <div className="rounded-lg border border-dashed border-[#E5E7EB] p-4 text-center text-xs text-neutral-400">
                  No document vector chunks retrieved for this request.
                </div>
              ) : (
                <div className="space-y-2">
                  {relevantChunks.map((chunk, idx) => (
                    <div key={chunk.chunk_id || idx} className="rounded-lg border border-[#E5E7EB] bg-white p-3 space-y-1.5 shadow-2xs">
                      <div className="flex items-center justify-between text-[10px] text-neutral-500 font-mono">
                        <span className="font-semibold text-neutral-800">Chunk {idx + 1}: {chunk.chunk_id}</span>
                        {chunk.similarity != null && (
                          <span className="text-blue-600 font-medium">
                            Similarity: {Math.round(chunk.similarity * 100)}%
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-neutral-400">
                        <span>{chunk.source || "Document"}</span>
                        {chunk.page != null && <span>• Page {chunk.page}</span>}
                      </div>
                      <p className="text-[11.5px] text-neutral-700 font-mono bg-[#F8F9FA] p-2 rounded border border-[#E5E7EB] whitespace-pre-wrap leading-relaxed">
                        {chunk.text}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* ================================================================ */}
        {/* TAB 3: AGENTS                                                   */}
        {/* ================================================================ */}
        {activeTab === "agents" && (
          <div className="space-y-4">
            {/* Header with View Toggle */}
            <div className="flex items-center justify-between border-b border-[#F3F4F6] pb-2">
              <div>
                <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider block">
                  Multi-Agent Execution
                </span>
                <span className="text-[10px] text-neutral-400 font-mono">
                  {executionTrace?.total_latency_ms ?? 0}ms total • Route: {executionTrace?.route || "AUTO"}
                </span>
              </div>

              {/* View Mode Toggle */}
              <div className="flex items-center rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-0.5 text-[11px] font-medium">
                <button
                  type="button"
                  onClick={() => setAgentViewMode("graph")}
                  className={`rounded-md px-2 py-0.5 transition cursor-pointer ${
                    agentViewMode === "graph"
                      ? "bg-white text-neutral-900 shadow-2xs font-semibold"
                      : "text-neutral-500 hover:text-neutral-900"
                  }`}
                >
                  Topology Graph
                </button>
                <button
                  type="button"
                  onClick={() => setAgentViewMode("list")}
                  className={`rounded-md px-2 py-0.5 transition cursor-pointer ${
                    agentViewMode === "list"
                      ? "bg-white text-neutral-900 shadow-2xs font-semibold"
                      : "text-neutral-500 hover:text-neutral-900"
                  }`}
                >
                  Timeline List
                </button>
              </div>
            </div>

            {/* View 1: Flowchart Architecture Topology Graph */}
            {agentViewMode === "graph" && (
              <div className="space-y-3">
                <AgentWorkflowGraph
                  executionTrace={executionTrace}
                  selectedAgentId={selectedAgent?.agent_id || selectedAgentId}
                  onSelectAgent={(id) => setSelectedAgentId(id)}
                />

                {/* Selected Agent Detailed Inspector */}
                {selectedAgent && (
                  <div className="rounded-xl border border-neutral-900/60 bg-white p-3.5 shadow-xs space-y-2.5 animate-in fade-in duration-150">
                    <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-2">
                      <div className="flex items-center gap-2">
                        {getAgentIcon(selectedAgent.agent_id)}
                        <div>
                          <h4 className="text-xs font-bold text-neutral-900">
                            {selectedAgent.agent_name}
                          </h4>
                          <span className="text-[10px] text-neutral-400">{selectedAgent.role}</span>
                        </div>
                      </div>
                      <div className="text-right">
                        <span
                          className={`text-[9.5px] px-2 py-0.5 rounded font-semibold ${
                            selectedAgent.status === "COMPLETED"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : selectedAgent.status === "SKIPPED"
                              ? "bg-neutral-100 text-neutral-500"
                              : selectedAgent.status === "FAILED"
                              ? "bg-rose-50 text-rose-700 border border-rose-200"
                              : "bg-blue-50 text-blue-700 border border-blue-200"
                          }`}
                        >
                          {selectedAgent.status}
                        </span>
                        {selectedAgent.latency_ms != null && selectedAgent.latency_ms > 0 && (
                          <span className="block text-[9.5px] text-neutral-400 font-mono mt-0.5">
                            {selectedAgent.latency_ms}ms
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[10.5px]">
                      <div className="rounded bg-[#F8F9FA] p-2 border border-[#E5E7EB]">
                        <span className="text-neutral-400 block text-[9.5px] uppercase font-medium">Model</span>
                        <span className="font-mono text-neutral-800 text-[11px] font-semibold">{selectedAgent.model || "N/A"}</span>
                      </div>
                      <div className="rounded bg-[#F8F9FA] p-2 border border-[#E5E7EB]">
                        <span className="text-neutral-400 block text-[9.5px] uppercase font-medium">Gateway</span>
                        <span className="font-mono text-neutral-800 text-[11px] font-semibold">{selectedAgent.gateway || "N/A"}</span>
                      </div>
                    </div>

                    {selectedAgent.input_summary && (
                      <div>
                        <span className="font-semibold text-neutral-700 block text-[10px] uppercase tracking-wider mb-1">
                          Input / Task Specification
                        </span>
                        <p className="text-[10.5px] text-neutral-600 font-mono bg-[#F8F9FA] p-2 rounded border border-[#E5E7EB] leading-relaxed">
                          {selectedAgent.input_summary}
                        </p>
                      </div>
                    )}

                    {selectedAgent.output_summary && (
                      <div>
                        <span className="font-semibold text-neutral-700 block text-[10px] uppercase tracking-wider mb-1">
                          Output / Agent Result
                        </span>
                        <p className="text-[10.5px] text-neutral-600 font-mono bg-[#F8F9FA] p-2 rounded border border-[#E5E7EB] leading-relaxed">
                          {selectedAgent.output_summary}
                        </p>
                      </div>
                    )}

                    {selectedAgent.evidence_refs && selectedAgent.evidence_refs.length > 0 && (
                      <div>
                        <span className="font-semibold text-neutral-700 block text-[10px] uppercase tracking-wider mb-1">
                          Evidence References
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {selectedAgent.evidence_refs.map((ref, rIdx) => (
                            <span key={rIdx} className="rounded bg-neutral-100 border border-neutral-200 px-1.5 py-0.5 font-mono text-[9.5px] text-neutral-700">
                              {ref}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* View 2: Timeline Cards List */}
            {agentViewMode === "list" && (
              <div className="space-y-2">
                {agents.map((agent, idx) => {
                  const isSelected = selectedAgent?.agent_id === agent.agent_id;
                  const isCompleted = agent.status === "COMPLETED";
                  const isSkipped = agent.status === "SKIPPED";
                  const isFailed = agent.status === "FAILED";

                  return (
                    <div
                      key={agent.agent_id}
                      onClick={() => setSelectedAgentId(agent.agent_id)}
                      className={`rounded-lg border p-3 transition cursor-pointer ${
                        isSelected
                          ? "border-[#111111] bg-neutral-50/70 shadow-xs"
                          : "border-[#E5E7EB] bg-white hover:border-neutral-300"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {getAgentIcon(agent.agent_id)}
                          <div>
                            <span className="text-xs font-semibold text-neutral-900 block leading-tight">
                              {agent.agent_name}
                            </span>
                            <span className="text-[10px] text-neutral-400">{agent.role}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <span
                            className={`text-[9.5px] px-1.5 py-0.5 rounded font-medium ${
                              isCompleted
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : isSkipped
                                ? "bg-neutral-100 text-neutral-500"
                                : isFailed
                                ? "bg-rose-50 text-rose-700 border border-rose-200"
                                : "bg-blue-50 text-blue-700 border border-blue-200"
                            }`}
                          >
                            {agent.status}
                          </span>
                          {agent.latency_ms != null && agent.latency_ms > 0 && (
                            <span className="block text-[9.5px] text-neutral-400 font-mono mt-0.5">
                              {agent.latency_ms}ms
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Expanded details when selected */}
                      {isSelected && (
                        <div className="mt-2.5 pt-2.5 border-t border-[#E5E7EB] space-y-1.5 text-[11px] text-neutral-600 animate-in fade-in duration-100">
                          <div className="grid grid-cols-2 gap-2 text-[10px] text-neutral-500 mb-1">
                            <div>
                              <span className="text-neutral-400 block">Model:</span>
                              <span className="font-mono text-neutral-800">{agent.model || "N/A"}</span>
                            </div>
                            <div>
                              <span className="text-neutral-400 block">Gateway:</span>
                              <span className="font-mono text-neutral-800">{agent.gateway || "N/A"}</span>
                            </div>
                          </div>
                          {agent.input_summary && (
                            <div>
                              <span className="font-medium text-neutral-700 block text-[10px] uppercase">Input:</span>
                              <p className="text-[10.5px] text-neutral-600 font-mono bg-white p-1.5 rounded border border-[#E5E7EB]">
                                {agent.input_summary}
                              </p>
                            </div>
                          )}
                          {agent.output_summary && (
                            <div>
                              <span className="font-medium text-neutral-700 block text-[10px] uppercase">Output:</span>
                              <p className="text-[10.5px] text-neutral-600 font-mono bg-white p-1.5 rounded border border-[#E5E7EB]">
                                {agent.output_summary}
                              </p>
                            </div>
                          )}
                          {agent.evidence_refs && agent.evidence_refs.length > 0 && (
                            <div>
                              <span className="font-medium text-neutral-700 block text-[10px] uppercase">Evidence References:</span>
                              <div className="flex flex-wrap gap-1 mt-0.5">
                                {agent.evidence_refs.map((ref, rIdx) => (
                                  <span key={rIdx} className="rounded bg-neutral-200/60 px-1 py-0.2 font-mono text-[9.5px] text-neutral-700">
                                    {ref}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
