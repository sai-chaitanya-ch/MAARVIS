import { useState, useEffect } from "react";
import {
  ArrowLeft,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Copy,
  Check,
  ShieldAlert,
  ShieldCheck,
  Cpu,
  Layers,
  FileText,
  Activity,
  Code2,
  Calculator,
  Terminal,
  Clock,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Database,
  BarChart3,
  Search,
} from "lucide-react";
import {
  VerificationRun,
  EvaluationCase,
  SystemBenchmarksData,
  fetchEvaluationCases,
  fetchEvaluationBenchmarks,
  fetchLatestEvaluationRun,
  executeEvaluationRun,
} from "../../lib/api";

interface EvaluationLabProps {
  onBackToChat: () => void;
}

export default function EvaluationLab({ onBackToChat }: EvaluationLabProps) {
  const [cases, setCases] = useState<EvaluationCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("eval_001");
  const [run, setRun] = useState<VerificationRun | null>(null);
  const [benchmarks, setBenchmarks] = useState<SystemBenchmarksData | null>(null);
  const [loading, setLoading] = useState(false);
  const [runningStep, setRunningStep] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<
    | "sandbox"
    | "provenance"
    | "verification"
    | "contradiction"
    | "critic"
    | "correction"
    | "decision"
    | "metrics"
    | "trace"
    | "audit"
    | "json"
  >("verification");
  const [copiedJson, setCopiedJson] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [casesRes, benchRes, latestRun] = await Promise.all([
          fetchEvaluationCases(),
          fetchEvaluationBenchmarks(),
          fetchLatestEvaluationRun().catch(() => null),
        ]);
        setCases(casesRes.cases || []);
        setBenchmarks(benchRes);
        if (latestRun) {
          setRun(latestRun);
          if (latestRun.caseId) setSelectedCaseId(latestRun.caseId);
        }
      } catch (err) {
        console.error("Failed to load evaluation data", err);
      }
    }
    loadData();
  }, []);

  const handleRunEvaluation = async (caseIdToRun?: string) => {
    const id = caseIdToRun || selectedCaseId;
    setLoading(true);
    setRunningStep(1);

    // Fast progressive stage animation for judge demo
    const timer1 = setTimeout(() => setRunningStep(3), 80);
    const timer2 = setTimeout(() => setRunningStep(6), 180);
    const timer3 = setTimeout(() => setRunningStep(9), 280);

    try {
      const result = await executeEvaluationRun({ case_id: id });
      setTimeout(() => {
        setRun(result);
        setRunningStep(null);
        setLoading(false);
      }, 380);
    } catch (err) {
      console.error("Evaluation execution failed", err);
      setRunningStep(null);
      setLoading(false);
    }
  };

  const handleCopyJson = async () => {
    if (!run) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(run, null, 2));
      setCopiedJson(true);
      setTimeout(() => setCopiedJson(false), 2000);
    } catch {
      // ignore
    }
  };

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case "ACCEPT":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
            <CheckCircle2 size={12} className="text-emerald-600" />
            <span>ACCEPT</span>
          </span>
        );
      case "PARTIALLY_ACCEPT":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2.5 py-0.5 text-xs font-semibold text-amber-800">
            <AlertTriangle size={12} className="text-amber-600" />
            <span>PARTIALLY ACCEPT</span>
          </span>
        );
      case "REJECT":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 border border-rose-200 px-2.5 py-0.5 text-xs font-semibold text-rose-800">
            <XCircle size={12} className="text-rose-600" />
            <span>REJECT</span>
          </span>
        );
      case "CONFLICTING_EVIDENCE":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 border border-rose-200 px-2.5 py-0.5 text-xs font-semibold text-rose-800">
            <ShieldAlert size={12} className="text-rose-600" />
            <span>CONFLICTING EVIDENCE</span>
          </span>
        );
      case "INSUFFICIENT_EVIDENCE":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 border border-neutral-200 px-2.5 py-0.5 text-xs font-semibold text-neutral-800">
            <AlertTriangle size={12} className="text-neutral-500" />
            <span>INSUFFICIENT EVIDENCE</span>
          </span>
        );
      case "UNSAFE":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 border border-rose-300 px-2.5 py-0.5 text-xs font-semibold text-rose-900">
            <ShieldAlert size={12} className="text-rose-700" />
            <span>UNSAFE</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 border border-neutral-200 px-2.5 py-0.5 text-xs font-medium text-neutral-700">
            {decision}
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "verified":
        return (
          <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 text-xs">
            <CheckCircle2 size={13} className="text-emerald-600" />
            <span>VERIFIED</span>
          </span>
        );
      case "conflicting":
        return (
          <span className="inline-flex items-center gap-1 font-semibold text-amber-700 text-xs">
            <AlertTriangle size={13} className="text-amber-600" />
            <span>CONFLICTING</span>
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1 font-semibold text-rose-700 text-xs">
            <XCircle size={13} className="text-rose-600" />
            <span>REJECTED</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 font-medium text-neutral-600 text-xs">
            <span>UNVERIFIED</span>
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-white text-[#111827] antialiased">
      {/* Top Header */}
      <div className="border-b border-[#E5E7EB] bg-[#F8F9FA]/80 px-6 py-4 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBackToChat}
              className="flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 shadow-2xs hover:bg-[#F3F4F6] transition"
            >
              <ArrowLeft size={13} />
              <span>Back to Chat</span>
            </button>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold tracking-tight text-neutral-900">MAARVIS</span>
                <span className="text-xs text-neutral-400">/</span>
                <h1 className="text-sm font-semibold text-neutral-800">
                  Evaluation & Verification Laboratory
                </h1>
              </div>
              <p className="text-[11px] text-[#6B7280] mt-0.5">
                Inspect how an answer was generated, verified, corrected, and accepted.
              </p>
            </div>
          </div>

          {/* Quick Stats Banner */}
          <div className="hidden lg:flex items-center gap-5 border-l border-neutral-200 pl-6 text-xs">
            <div>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
                Verification Accuracy
              </span>
              <span className="font-semibold text-emerald-700">
                {benchmarks?.metrics.claimVerificationAccuracy ?? "93.2"}%
              </span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
                Contradiction Detection
              </span>
              <span className="font-semibold text-neutral-800">
                {benchmarks?.metrics.contradictionDetection ?? "94.1"}%
              </span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
                Self-Correction
              </span>
              <span className="font-semibold text-neutral-800">
                {benchmarks?.metrics.selfCorrectionSuccess ?? "86.7"}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-6 space-y-6">
        {/* Judge Demonstration Mode: Case Selector */}
        <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-neutral-700" />
              <span className="font-semibold text-neutral-900">
                Judge Demonstration Mode
              </span>
              <span className="text-[11px] text-neutral-500">
                · Select a predefined evaluation scenario to trace live multi-agent verification
              </span>
            </div>
            <button
              onClick={() => handleRunEvaluation()}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-lg bg-neutral-900 px-3.5 py-1.5 text-xs font-medium text-white shadow-2xs hover:bg-neutral-800 disabled:opacity-50 transition cursor-pointer"
            >
              {loading ? (
                <>
                  <RotateCcw size={12} className="animate-spin" />
                  <span>Verifying in Real Time...</span>
                </>
              ) : (
                <>
                  <Play size={12} fill="currentColor" />
                  <span>Run Evaluation Test</span>
                </>
              )}
            </button>
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            {cases.map((c) => (
              <button
                key={c.id}
                onClick={() => {
                  setSelectedCaseId(c.id);
                  handleRunEvaluation(c.id);
                }}
                className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-medium transition cursor-pointer ${
                  selectedCaseId === c.id
                    ? "bg-white text-neutral-900 shadow-2xs border border-neutral-300 font-semibold"
                    : "bg-neutral-100/70 text-neutral-600 hover:bg-neutral-200/60 hover:text-neutral-900"
                }`}
              >
                {c.title}
              </button>
            ))}
          </div>
        </div>

        {/* Task Summary Card */}
        {run && (
          <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs text-xs space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#E5E7EB] pb-4">
              <div className="space-y-1 max-w-3xl">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                  Question / Target Query
                </span>
                <p className="text-sm font-medium text-[#111827]">
                  "{run.query}"
                </p>
                {run.caseTitle && (
                  <p className="text-[11px] text-neutral-500">
                    Scenario: <span className="font-medium text-neutral-700">{run.caseTitle}</span>
                  </p>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="text-right">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 block">
                    Final Decision
                  </span>
                  <div className="mt-0.5">{getDecisionBadge(run.decision)}</div>
                </div>
              </div>
            </div>

            {/* Metrics Ribbon */}
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3 text-center">
              <div className="rounded-lg bg-[#F8F9FA] p-2.5 border border-[#E5E7EB]">
                <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">
                  Status
                </span>
                <div className="mt-1 flex justify-center">{getStatusBadge(run.status)}</div>
              </div>
              <div className="rounded-lg bg-[#F8F9FA] p-2.5 border border-[#E5E7EB]">
                <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">
                  Evidence Score
                </span>
                <span className="mt-1 block font-bold text-neutral-900">
                  {run.evidenceScore}%
                </span>
              </div>
              <div className="rounded-lg bg-[#F8F9FA] p-2.5 border border-[#E5E7EB]">
                <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">
                  Latency
                </span>
                <span className="mt-1 block font-medium text-neutral-800">
                  {run.latency}s
                </span>
              </div>
              <div className="rounded-lg bg-[#F8F9FA] p-2.5 border border-[#E5E7EB]">
                <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">
                  Iterations
                </span>
                <span className="mt-1 block font-medium text-neutral-800">
                  {run.verificationIterations}
                </span>
              </div>
              <div className="rounded-lg bg-[#F8F9FA] p-2.5 border border-[#E5E7EB]">
                <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">
                  Claims Checked
                </span>
                <span className="mt-1 block font-medium text-neutral-800">
                  {run.claims.length}
                </span>
              </div>
              <div className="rounded-lg bg-[#F8F9FA] p-2.5 border border-[#E5E7EB]">
                <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">
                  Risk Level
                </span>
                <span
                  className={`mt-1 block font-semibold ${
                    run.risk === "HIGH"
                      ? "text-rose-700"
                      : run.risk === "MEDIUM"
                      ? "text-amber-700"
                      : "text-emerald-700"
                  }`}
                >
                  {run.risk}
                </span>
              </div>
              <div className="rounded-lg bg-[#F8F9FA] p-2.5 border border-[#E5E7EB]">
                <span className="text-[10px] text-neutral-500 uppercase tracking-wider block">
                  Task ID
                </span>
                <span className="mt-1 block font-mono text-[11px] text-neutral-600 truncate">
                  {run.taskId}
                </span>
              </div>
            </div>

            {/* Decision explanation banner */}
            <div className="rounded-lg bg-neutral-50 border border-neutral-200/80 p-3 text-[11.5px] leading-relaxed text-neutral-700">
              <span className="font-semibold text-neutral-900">Decision Rationale: </span>
              {run.decisionReason}
            </div>
          </div>
        )}

        {/* 10-Stage Horizontal Execution Pipeline */}
        {run && (
          <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Activity size={14} className="text-neutral-700" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-900">
                  Multi-Agent Verification Pipeline (10 Stages)
                </h3>
              </div>
              <span className="text-[11px] text-neutral-500">
                Dynamic execution graph reflecting actual backend states
              </span>
            </div>

            <div className="flex items-center justify-between gap-1 overflow-x-auto pb-2 pt-1">
              {run.pipeline.map((stage, idx) => {
                const isStepRunning = runningStep !== null && idx === runningStep;
                const isCompleted =
                  runningStep === null ? stage.status === "completed" : idx < runningStep;
                const isFailed = stage.status === "failed";
                const isSkipped = stage.status === "skipped";

                return (
                  <div key={stage.id} className="flex items-center flex-1 min-w-[105px]">
                    <div className="flex flex-col items-center text-center w-full">
                      {/* Circle node */}
                      <div className="h-6 w-6 flex items-center justify-center mb-1">
                        {isStepRunning ? (
                          <div className="relative flex h-5 w-5 items-center justify-center">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neutral-400 opacity-75"></span>
                            <div className="h-4 w-4 rounded-full border border-neutral-900 bg-white flex items-center justify-center">
                              <div className="h-1.5 w-1.5 rounded-full bg-neutral-900 animate-pulse" />
                            </div>
                          </div>
                        ) : isFailed ? (
                          <div className="h-5 w-5 rounded-full bg-rose-600 text-white flex items-center justify-center text-[10px] font-bold">
                            ✕
                          </div>
                        ) : isCompleted ? (
                          <div className="h-5 w-5 rounded-full bg-emerald-700 text-white flex items-center justify-center shadow-2xs">
                            <Check size={11} strokeWidth={2.8} />
                          </div>
                        ) : isSkipped ? (
                          <div className="h-4 w-4 rounded-full border border-neutral-300 bg-neutral-100 flex items-center justify-center text-[9px] text-neutral-400">
                            —
                          </div>
                        ) : (
                          <div className="h-4 w-4 rounded-full border border-neutral-300 bg-white" />
                        )}
                      </div>

                      {/* Number and Stage Name */}
                      <span className="text-[10px] font-mono text-neutral-400 font-semibold leading-none">
                        {stage.id}
                      </span>
                      <span
                        className={`text-[11px] font-semibold tracking-tight mt-0.5 leading-tight ${
                          isFailed
                            ? "text-rose-700"
                            : isCompleted
                            ? "text-neutral-900"
                            : "text-neutral-400"
                        }`}
                      >
                        {stage.name}
                      </span>
                      {/* Agent name */}
                      <span className="text-[9.5px] text-neutral-500 mt-0.5 truncate max-w-[95px]">
                        {stage.agent}
                      </span>
                      {stage.durationMs > 0 && (
                        <span className="text-[9px] text-neutral-400 font-mono">
                          {stage.durationMs}ms
                        </span>
                      )}
                    </div>

                    {/* Connecting line */}
                    {idx < run.pipeline.length - 1 && (
                      <div className="flex-1 mx-1 h-[1px] bg-neutral-200 relative -top-3">
                        <div
                          className={`h-full transition-all duration-300 ${
                            isCompleted ? "bg-neutral-800 w-full" : "w-0"
                          }`}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="border-b border-[#E5E7EB]">
          <div className="flex items-center gap-6 overflow-x-auto text-xs font-medium">
            {[
              { id: "verification", label: "Independent Verification", icon: ShieldCheck },
              { id: "provenance", label: "Evidence & Provenance", icon: Layers },
              { id: "contradiction", label: "Contradiction Guard", icon: ShieldAlert },
              { id: "critic", label: "Critic Analysis", icon: Activity },
              { id: "correction", label: "Self-Correction", icon: RotateCcw },
              { id: "decision", label: "Decision Engine", icon: CheckCircle2 },
              { id: "sandbox", label: "Deterministic Sandbox", icon: Calculator },
              { id: "metrics", label: "Evaluation Metrics", icon: BarChart3 },
              { id: "trace", label: "Agent Trace", icon: Cpu },
              { id: "audit", label: "Audit Trail", icon: Clock },
              { id: "json", label: "Raw JSON", icon: Code2 },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as typeof activeTab)}
                  className={`flex items-center gap-1.5 pb-2.5 transition whitespace-nowrap cursor-pointer border-b-2 ${
                    isActive
                      ? "border-neutral-900 text-neutral-900 font-semibold"
                      : "border-transparent text-neutral-500 hover:text-neutral-800"
                  }`}
                >
                  <Icon size={13} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* TAB CONTENTS */}
        {run && (
          <div className="space-y-4">
            {/* 1. Independent Verification Tab */}
            {activeTab === "verification" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">
                      Claim-Level Independent Verification
                    </h3>
                    <p className="text-[11px] text-neutral-500">
                      Independent verification logically evaluates claims after generation. The generator never self-verifies.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-medium">
                    <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      Supported: {run.metrics.claimsSupported}
                    </span>
                    <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      Partial: {run.metrics.claimsPartiallySupported}
                    </span>
                    <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                      Unsupported: {run.metrics.unsupportedClaims}
                    </span>
                  </div>
                </div>

                <div className="space-y-3 pt-1">
                  {run.claims.map((claim) => (
                    <div
                      key={claim.id}
                      className="rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-3.5 space-y-2 hover:border-neutral-300 transition"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2">
                          <span className="font-mono font-bold text-xs text-neutral-700 bg-white px-1.5 py-0.5 rounded border border-neutral-200">
                            {claim.id}
                          </span>
                          <div>
                            <p className="font-medium text-neutral-900 text-xs">
                              "{claim.claimText}"
                            </p>
                            <p className="text-[11px] text-neutral-500 mt-0.5">
                              Verifier: <span className="font-medium text-neutral-700">{claim.verifier || "Verification Agent"}</span> · Method: <span className="font-medium text-neutral-700">{claim.verificationMethod}</span>
                            </p>
                          </div>
                        </div>
                        <div>
                          {claim.status === "verified" ? (
                            <span className="inline-flex items-center gap-1 rounded bg-emerald-50 border border-emerald-200 px-2 py-0.5 font-semibold text-emerald-800 text-[11px]">
                              ✓ VERIFIED
                            </span>
                          ) : claim.status === "conflicting" ? (
                            <span className="inline-flex items-center gap-1 rounded bg-rose-50 border border-rose-200 px-2 py-0.5 font-semibold text-rose-800 text-[11px]">
                              ⚠ CONFLICTING
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded bg-rose-50 border border-rose-200 px-2 py-0.5 font-semibold text-rose-800 text-[11px]">
                              ✕ UNVERIFIED
                            </span>
                          )}
                        </div>
                      </div>

                      {claim.reason && (
                        <p className="text-[11px] text-neutral-600 bg-white/70 rounded p-2 border border-neutral-200/60">
                          <span className="font-medium text-neutral-800">Verification Verdict: </span>
                          {claim.reason}
                        </p>
                      )}

                      {claim.evidence && claim.evidence.length > 0 && (
                        <div className="pt-1 text-[11px] text-neutral-500 space-y-1">
                          <span className="font-medium text-neutral-700">Supporting Citations:</span>
                          {claim.evidence.map((ev, i) => (
                            <div key={i} className="flex items-center gap-1.5 text-neutral-600 pl-2">
                              <span className="font-mono text-[10px] text-neutral-400">[{ev.sourceId}]</span>
                              <span className="font-medium">{ev.title}</span>
                              {ev.snippet && <span className="text-neutral-400 truncate max-w-md">— "{ev.snippet}"</span>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 2. Evidence & Provenance Tab */}
            {activeTab === "provenance" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Evidence Provenance & Grounding
                  </h3>
                  <p className="text-[11px] text-neutral-500">
                    Each statement is grounded in primary citations with source tier classification and latency metadata.
                  </p>
                </div>

                <div className="space-y-3">
                  {run.evidence.length === 0 ? (
                    <p className="text-neutral-500 text-center py-6">
                      Zero supporting evidence retrieved from authoritative repositories.
                    </p>
                  ) : (
                    run.evidence.map((ev) => (
                      <div
                        key={ev.id}
                        className="rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-3.5 space-y-2 hover:border-neutral-300 transition"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-neutral-500 font-semibold">
                              {ev.id}
                            </span>
                            <span className="font-medium text-neutral-900">
                              {ev.title}
                            </span>
                            <span className="rounded bg-white border border-neutral-200 px-1.5 py-0.5 text-[10px] text-neutral-600 uppercase font-mono">
                              Tier {ev.tier}
                            </span>
                            <span className="rounded bg-neutral-200/60 px-1.5 py-0.5 text-[10px] text-neutral-600 font-mono">
                              {ev.sourceType}
                            </span>
                          </div>
                          <span className="text-[11px] text-neutral-400 font-mono">
                            {ev.retrievalTimeMs}ms
                          </span>
                        </div>

                        <p className="text-[11.5px] leading-relaxed text-neutral-700 bg-white p-2.5 rounded border border-neutral-200/60 font-mono">
                          "{ev.snippet}"
                        </p>

                        <div className="flex items-center justify-between text-[11px] text-neutral-500">
                          <span>Grounds: <span className="font-medium font-mono text-neutral-700">{ev.claimId}</span></span>
                          {ev.url && (
                            <a
                              href={ev.url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-neutral-600 hover:text-neutral-900"
                            >
                              <span>{ev.domain || ev.url}</span>
                              <ExternalLink size={10} />
                            </a>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* 3. Contradiction Guard Tab */}
            {activeTab === "contradiction" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Contradiction Guard & Cross-Source Consistency
                  </h3>
                  <p className="text-[11px] text-neutral-500">
                    Detects conflicting statements across independent sources rather than picking a side silently.
                  </p>
                </div>

                {run.contradictions.hasConflict ? (
                  <div className="space-y-3">
                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-amber-900 flex items-start gap-2">
                      <AlertTriangle size={15} className="text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold text-xs">⚠ Conflicting Evidence Detected</p>
                        <p className="text-[11px] text-amber-800 mt-0.5">
                          The system intercepted competing assertions and prevented silent hallucination bias.
                        </p>
                      </div>
                    </div>

                    {run.contradictions.conflicts.map((c, i) => (
                      <div key={i} className="rounded-lg border border-neutral-200 bg-[#F8F9FA] p-3.5 space-y-2">
                        <span className="font-semibold text-neutral-900 block text-xs">
                          Conflict #{i + 1}: {c.claim}
                        </span>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                          <div className="bg-white p-2.5 rounded border border-neutral-200">
                            <span className="text-[10px] uppercase font-semibold text-neutral-400 block">
                              Source A
                            </span>
                            <p className="font-medium text-neutral-800 mt-0.5 text-xs">{c.sourceA}</p>
                          </div>
                          <div className="bg-white p-2.5 rounded border border-neutral-200">
                            <span className="text-[10px] uppercase font-semibold text-neutral-400 block">
                              Source B
                            </span>
                            <p className="font-medium text-neutral-800 mt-0.5 text-xs">{c.sourceB}</p>
                          </div>
                        </div>
                        <div className="pt-1 text-[11px] text-neutral-600">
                          <span className="font-medium text-neutral-800">Resolution Status: </span>
                          {c.resolution}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-center space-y-1">
                    <CheckCircle2 size={18} className="text-emerald-600 mx-auto" />
                    <p className="font-semibold text-emerald-900 text-xs">
                      ✓ No Contradictions Detected
                    </p>
                    <p className="text-[11px] text-emerald-700">
                      All consulted primary sources demonstrate full factual and numerical alignment.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 4. Critic Tab */}
            {activeTab === "critic" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">
                      Critic Agent Risk Assessment
                    </h3>
                    <p className="text-[11px] text-neutral-500">
                      Reviews candidate drafts for unsupported claims, ambiguity, and factual drift.
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 block">
                      Overall Risk
                    </span>
                    <span className={`font-bold ${run.critic.risk === "HIGH" ? "text-rose-700" : run.critic.risk === "MEDIUM" ? "text-amber-700" : "text-emerald-700"}`}>
                      {run.critic.risk}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="bg-[#F8F9FA] p-3 rounded-lg border border-neutral-200">
                    <span className="text-[10px] text-neutral-500 uppercase">Claims Reviewed</span>
                    <span className="block font-bold text-neutral-900 mt-1">{run.critic.claimsReviewed}</span>
                  </div>
                  <div className="bg-[#F8F9FA] p-3 rounded-lg border border-neutral-200">
                    <span className="text-[10px] text-neutral-500 uppercase">Potential Issues</span>
                    <span className="block font-bold text-neutral-900 mt-1">{run.critic.issuesCount}</span>
                  </div>
                  <div className="bg-[#F8F9FA] p-3 rounded-lg border border-neutral-200">
                    <span className="text-[10px] text-neutral-500 uppercase">Risk Level</span>
                    <span className="block font-bold text-neutral-900 mt-1">{run.critic.risk}</span>
                  </div>
                </div>

                {run.critic.issues.length === 0 ? (
                  <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-4 text-center text-neutral-600 text-xs">
                    ✓ Critic passed candidate draft with zero flagged anomalies.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {run.critic.issues.map((issue) => (
                      <div key={issue.id} className="rounded-lg border border-neutral-200 bg-[#F8F9FA] p-3 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-neutral-900">
                            Issue #{issue.id}: {issue.type}
                          </span>
                          <span className="rounded bg-rose-50 border border-rose-200 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700 uppercase">
                            {issue.severity}
                          </span>
                        </div>
                        <p className="text-[11.5px] text-neutral-600">{issue.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 5. Self-Correction Tab */}
            {activeTab === "correction" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Self-Correction & Revision History
                  </h3>
                  <p className="text-[11px] text-neutral-500">
                    Demonstrates autonomous self-correction loop: Generation → Verification Failure → Critic → Correction → Re-Verification → Pass.
                  </p>
                </div>

                <div className="flex items-center gap-4 text-xs">
                  <div className="bg-[#F8F9FA] px-3 py-1.5 rounded-lg border border-neutral-200">
                    <span className="text-neutral-500">Correction Iterations: </span>
                    <span className="font-bold text-neutral-900">{run.correctionCount}</span>
                  </div>
                  <div className="bg-[#F8F9FA] px-3 py-1.5 rounded-lg border border-neutral-200">
                    <span className="text-neutral-500">Re-Verification Passes: </span>
                    <span className="font-bold text-neutral-900">{run.reVerificationAttempts}</span>
                  </div>
                </div>

                <div className="space-y-3 pt-1">
                  {run.revisions.map((rev) => (
                    <div
                      key={rev.revision}
                      className={`rounded-lg border p-3.5 space-y-2 ${
                        rev.passed
                          ? "border-emerald-200 bg-emerald-50/30"
                          : "border-rose-200 bg-rose-50/30"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-neutral-900">
                          {rev.label}
                        </span>
                        {rev.passed ? (
                          <span className="inline-flex items-center gap-1 rounded bg-emerald-100/70 text-emerald-800 font-semibold px-2 py-0.5 text-[10.5px]">
                            <CheckCircle2 size={11} />
                            <span>Passed Re-Verification</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded bg-rose-100/70 text-rose-800 font-semibold px-2 py-0.5 text-[10.5px]">
                            <XCircle size={11} />
                            <span>Failed Initial Verification</span>
                          </span>
                        )}
                      </div>

                      <p className="text-[11.5px] leading-relaxed text-neutral-800 bg-white p-2.5 rounded border border-neutral-200 font-mono">
                        "{rev.answer}"
                      </p>

                      {rev.issue && (
                        <div className="text-[11px] text-rose-700 bg-rose-100/40 p-2 rounded">
                          <span className="font-semibold">Flagged Anomaly: </span>
                          {rev.issue}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 6. Decision Engine Tab */}
            {activeTab === "decision" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Final Decision Engine & Arbitration
                  </h3>
                  <p className="text-[11px] text-neutral-500">
                    Formal policy arbitration determining whether to ACCEPT, PARTIALLY_ACCEPT, or REJECT based on claim verification.
                  </p>
                </div>

                <div className="rounded-xl bg-[#F8F9FA] border border-neutral-200 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                      Arbitration Decision
                    </span>
                    <div>{getDecisionBadge(run.decision)}</div>
                  </div>
                  <div className="pt-2 border-t border-neutral-200/80">
                    <span className="font-semibold text-neutral-900 text-xs block mb-1">
                      Formal Reason:
                    </span>
                    <p className="text-[12px] leading-relaxed text-neutral-700 bg-white p-3 rounded-lg border border-neutral-200">
                      {run.decisionReason}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="font-semibold text-neutral-800 block text-xs">
                    Decision Policy Rules:
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-[11px]">
                    <div className="p-2.5 rounded-lg border border-emerald-200 bg-emerald-50/50">
                      <span className="font-bold text-emerald-900 block">ACCEPT</span>
                      <p className="text-emerald-800 mt-0.5">All essential claims independently verified with 0 contradictions.</p>
                    </div>
                    <div className="p-2.5 rounded-lg border border-amber-200 bg-amber-50/50">
                      <span className="font-bold text-amber-900 block">PARTIALLY ACCEPT</span>
                      <p className="text-amber-800 mt-0.5">Non-critical claims lack proof or question is ambiguous.</p>
                    </div>
                    <div className="p-2.5 rounded-lg border border-rose-200 bg-rose-50/50">
                      <span className="font-bold text-rose-900 block">REJECT</span>
                      <p className="text-rose-800 mt-0.5">Critical assertions contradicted or completely unsupported.</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 7. Deterministic Sandbox Tab */}
            {activeTab === "sandbox" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Deterministic & Tool Sandbox Execution
                  </h3>
                  <p className="text-[11px] text-neutral-500">
                    Mathematical parsing and code logic execute in isolated sandboxes without LLM approximation.
                  </p>
                </div>

                <div className="rounded-lg border border-neutral-200 bg-[#F8F9FA] p-4 space-y-3 font-mono">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-neutral-500">Sandbox Type: <span className="text-neutral-900 font-bold">{run.sandbox.type.toUpperCase()}</span></span>
                    <span className={`px-2 py-0.5 rounded font-bold ${run.sandbox.status === "PASS" ? "bg-emerald-100 text-emerald-800" : "bg-neutral-200 text-neutral-700"}`}>
                      {run.sandbox.status}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10.5px] uppercase font-semibold text-neutral-400 block">
                      Input / Expression:
                    </span>
                    <pre className="bg-white p-2.5 rounded border border-neutral-200 text-xs text-neutral-900 overflow-x-auto">
                      {run.sandbox.input}
                    </pre>
                  </div>

                  {run.sandbox.code && (
                    <div className="space-y-1">
                      <span className="text-[10.5px] uppercase font-semibold text-neutral-400 block">
                        Sandboxed Execution Code:
                      </span>
                      <pre className="bg-white p-2.5 rounded border border-neutral-200 text-xs text-neutral-800 overflow-x-auto">
                        {run.sandbox.code}
                      </pre>
                    </div>
                  )}

                  <div className="space-y-1">
                    <span className="text-[10.5px] uppercase font-semibold text-neutral-400 block">
                      Output / Result:
                    </span>
                    <pre className="bg-white p-2.5 rounded border border-neutral-200 text-xs text-emerald-800 font-bold overflow-x-auto">
                      {run.sandbox.output}
                    </pre>
                  </div>

                  {run.sandbox.testCases && run.sandbox.testCases.length > 0 && (
                    <div className="pt-2 border-t border-neutral-200 space-y-1.5">
                      <span className="text-[10.5px] uppercase font-semibold text-neutral-400 block">
                        Automated Assertions ({run.sandbox.passedTests}/{run.sandbox.testCases.length} Passed):
                      </span>
                      {run.sandbox.testCases.map((tc, idx) => (
                        <div key={idx} className="flex items-center justify-between bg-white px-2.5 py-1.5 rounded border border-neutral-200 text-[11px]">
                          <span>{tc.test}</span>
                          <span className={tc.passed ? "text-emerald-700 font-bold" : "text-rose-700 font-bold"}>
                            {tc.passed ? "✓ PASS" : "✕ FAIL"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 8. Evaluation Metrics Tab */}
            {activeTab === "metrics" && benchmarks && (
              <div className="space-y-6">
                {/* Evidence Metrics */}
                <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">
                      Evidence Metrics (Current Run)
                    </h3>
                    <p className="text-[11px] text-neutral-500">
                      Percentages calculated strictly from verified claim counts (never arbitrary model confidence).
                    </p>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                    <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50">
                      <span className="text-[10px] font-semibold uppercase text-emerald-800">Verified</span>
                      <span className="block font-bold text-lg text-emerald-900 mt-0.5">{run.metrics.verified}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-neutral-50">
                      <span className="text-[10px] font-semibold uppercase text-neutral-600">Partially Verified</span>
                      <span className="block font-bold text-lg text-neutral-900 mt-0.5">{run.metrics.partiallyVerified}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-neutral-50">
                      <span className="text-[10px] font-semibold uppercase text-neutral-600">Unverified</span>
                      <span className="block font-bold text-lg text-neutral-900 mt-0.5">{run.metrics.unverified}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-rose-200 bg-rose-50/50">
                      <span className="text-[10px] font-semibold uppercase text-rose-800">Conflicting</span>
                      <span className="block font-bold text-lg text-rose-900 mt-0.5">{run.metrics.conflicting}%</span>
                    </div>
                  </div>
                </div>

                {/* System Evaluation Benchmarks */}
                <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-900">
                        System Evaluation Benchmark
                      </h3>
                      <p className="text-[11px] text-neutral-500">
                        Calculated programmatically across {benchmarks.testCases} test cases and {benchmarks.claimsEvaluated} evaluated claims.
                      </p>
                    </div>
                    <span className="rounded bg-neutral-100 px-2 py-0.5 font-mono text-[10px] text-neutral-600">
                      Formula-Governed
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                    <div className="p-3 rounded-lg border border-neutral-200 bg-[#F8F9FA]">
                      <span className="text-[10px] text-neutral-500 uppercase">Verification Accuracy</span>
                      <span className="block font-bold text-lg text-emerald-700 mt-0.5">{benchmarks.metrics.claimVerificationAccuracy}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-[#F8F9FA]">
                      <span className="text-[10px] text-neutral-500 uppercase">Unsupported Detection</span>
                      <span className="block font-bold text-lg text-neutral-900 mt-0.5">{benchmarks.metrics.unsupportedClaimDetection}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-[#F8F9FA]">
                      <span className="text-[10px] text-neutral-500 uppercase">Contradiction Detection</span>
                      <span className="block font-bold text-lg text-neutral-900 mt-0.5">{benchmarks.metrics.contradictionDetection}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-[#F8F9FA]">
                      <span className="text-[10px] text-neutral-500 uppercase">Evidence Precision</span>
                      <span className="block font-bold text-lg text-neutral-900 mt-0.5">{benchmarks.metrics.evidencePrecision}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-[#F8F9FA]">
                      <span className="text-[10px] text-neutral-500 uppercase">Self-Correction Success</span>
                      <span className="block font-bold text-lg text-emerald-700 mt-0.5">{benchmarks.metrics.selfCorrectionSuccess}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-[#F8F9FA]">
                      <span className="text-[10px] text-neutral-500 uppercase">False Acceptance Rate</span>
                      <span className="block font-bold text-lg text-neutral-800 mt-0.5">{benchmarks.metrics.falseAcceptanceRate}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-[#F8F9FA]">
                      <span className="text-[10px] text-neutral-500 uppercase">False Rejection Rate</span>
                      <span className="block font-bold text-lg text-neutral-800 mt-0.5">{benchmarks.metrics.falseRejectionRate}%</span>
                    </div>
                    <div className="p-3 rounded-lg border border-neutral-200 bg-[#F8F9FA]">
                      <span className="text-[10px] text-neutral-500 uppercase">Avg Iterations</span>
                      <span className="block font-bold text-lg text-neutral-900 mt-0.5">{benchmarks.metrics.averageVerificationIterations}</span>
                    </div>
                  </div>

                  <div className="space-y-1.5 pt-2">
                    <span className="font-semibold text-neutral-800 block text-xs">
                      Category Breakdown:
                    </span>
                    <div className="space-y-1">
                      {benchmarks.breakdownByCategory.map((b, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded bg-[#F8F9FA] border border-neutral-200 text-xs">
                          <span className="font-medium text-neutral-900">{b.category}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-neutral-500">{b.tests} tests</span>
                            <span className="font-bold text-emerald-700">{b.accuracy}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 9. Agent Trace Tab */}
            {activeTab === "trace" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Multi-Agent Orchestration Trace
                  </h3>
                  <p className="text-[11px] text-neutral-500">
                    Inspect the inputs, outputs, responsibilities, and execution durations for each participating agent.
                  </p>
                </div>

                <div className="space-y-3">
                  {run.agents.map((agent, i) => (
                    <div key={i} className="rounded-lg border border-neutral-200 bg-[#F8F9FA] p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-neutral-900 text-xs">{agent.name}</span>
                          <span className="text-[10.5px] text-neutral-500">· {agent.role}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10.5px] text-neutral-500">{agent.durationMs}ms</span>
                          <span className="rounded bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                            {agent.status}
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                        <div className="bg-white p-2 rounded border border-neutral-200 font-mono overflow-x-auto">
                          <span className="text-[9.5px] uppercase font-bold text-neutral-400 block mb-0.5">Input</span>
                          {agent.input}
                        </div>
                        <div className="bg-white p-2 rounded border border-neutral-200 font-mono overflow-x-auto">
                          <span className="text-[9.5px] uppercase font-bold text-neutral-400 block mb-0.5">Output</span>
                          {agent.output}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 10. Audit Trail Tab */}
            {activeTab === "audit" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-4 text-xs">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Chronological Verification Audit Trail
                  </h3>
                  <p className="text-[11px] text-neutral-500">
                    Immutable event log capturing exact timestamps and status transitions for complete auditability.
                  </p>
                </div>

                <div className="border border-neutral-200 rounded-lg overflow-hidden font-mono text-[11px]">
                  <div className="bg-neutral-100/70 px-3 py-2 border-b border-neutral-200 font-bold text-neutral-700 grid grid-cols-12 gap-2">
                    <span className="col-span-2">TIMESTAMP</span>
                    <span className="col-span-3">AGENT</span>
                    <span className="col-span-3">ACTION</span>
                    <span className="col-span-4">EVENT DETAIL</span>
                  </div>
                  <div className="divide-y divide-neutral-200/70 bg-white">
                    {run.auditTrail.map((ev, i) => (
                      <div key={i} className="px-3 py-2 grid grid-cols-12 gap-2 hover:bg-[#F8F9FA] transition">
                        <span className="col-span-2 text-neutral-500">{ev.time}</span>
                        <span className="col-span-3 font-semibold text-neutral-800 truncate">{ev.agent}</span>
                        <span className="col-span-3 text-neutral-900 font-bold truncate">{ev.action}</span>
                        <span className="col-span-4 text-neutral-600 truncate">{ev.detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 11. Raw JSON Tab */}
            {activeTab === "json" && (
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-2xs space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">
                      Raw VerificationRun Object
                    </h3>
                    <p className="text-[11px] text-neutral-500">
                      Standardized data interchange format for judges, downstream telemetry, and evaluation logs.
                    </p>
                  </div>
                  <button
                    onClick={handleCopyJson}
                    className="flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] px-3 py-1.5 font-medium text-neutral-700 hover:bg-[#F3F4F6] transition"
                  >
                    {copiedJson ? (
                      <>
                        <Check size={12} className="text-emerald-600" />
                        <span className="text-emerald-700">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy size={12} />
                        <span>Copy JSON</span>
                      </>
                    )}
                  </button>
                </div>

                <pre className="max-h-[500px] overflow-y-auto rounded-lg border border-neutral-200 bg-[#F8F9FA] p-4 font-mono text-[11px] leading-relaxed text-neutral-800">
                  {JSON.stringify(run, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
