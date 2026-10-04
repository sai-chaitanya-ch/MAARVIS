import React from "react";
import {
  BrainCircuit,
  Layers,
  Search,
  Database,
  Code,
  Terminal,
  ShieldCheck,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowDown,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { AgentRunRecord, ExecutionTrace } from "../lib/api";

interface AgentWorkflowGraphProps {
  executionTrace?: ExecutionTrace;
  selectedAgentId: string | null;
  onSelectAgent: (agentId: string) => void;
}

export default function AgentWorkflowGraph({
  executionTrace,
  selectedAgentId,
  onSelectAgent,
}: AgentWorkflowGraphProps) {
  const agents = executionTrace?.agents ?? [];
  const route = executionTrace?.route ?? "AUTO";
  const engine = executionTrace?.routing_engine ?? "";
  const isDirect = route === "DIRECT_FAST";

  const getAgent = (id: string): AgentRunRecord | undefined => {
    return agents.find((a) => a.agent_id === id);
  };

  const jev = getAgent("jev_decision");
  const marvis = getAgent("marvis_router");
  const researcher = getAgent("researcher_agent");
  const rag = getAgent("rag_agent");
  const coder = getAgent("coder_agent");
  const sandbox = getAgent("ast_sandbox");
  const verifier = getAgent("fact_verifier");
  const synthesizer = getAgent("synthesizer");

  // Node status helper styling
  const getNodeStyle = (agent?: AgentRunRecord, isSelected?: boolean) => {
    const status = agent?.status ?? "SKIPPED";
    const isCompleted = status === "COMPLETED";
    const isFailed = status === "FAILED";
    const isSkipped = status === "SKIPPED";

    let border = "border-[#E5E7EB]";
    let bg = "bg-white";
    let text = "text-neutral-900";
    let badgeBg = "bg-neutral-100 text-neutral-500";

    if (isCompleted) {
      border = "border-emerald-300";
      bg = "bg-emerald-50/30";
      badgeBg = "bg-emerald-50 text-emerald-700 border border-emerald-200";
    } else if (isFailed) {
      border = "border-rose-300";
      bg = "bg-rose-50/30";
      badgeBg = "bg-rose-50 text-rose-700 border border-rose-200";
    } else if (isSkipped) {
      border = "border-neutral-200 border-dashed";
      bg = "bg-[#FBFBFC]";
      text = "text-neutral-400";
      badgeBg = "bg-neutral-100 text-neutral-400";
    }

    if (isSelected) {
      border = "border-neutral-900 ring-2 ring-neutral-900/10";
      bg = isCompleted ? "bg-emerald-50/60" : "bg-neutral-50";
    }

    return { border, bg, text, badgeBg, isCompleted, isSkipped, isFailed };
  };

  return (
    <div className="space-y-4 py-2">
      {/* Workflow Diagram Card */}
      <div className="rounded-xl border border-[#E5E7EB] bg-[#FBFBFC] p-4 text-[#111111] shadow-2xs">
        <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-2.5 mb-3.5">
          <div className="flex items-center gap-2">
            <Layers size={14} className="text-neutral-700" />
            <span className="text-xs font-semibold text-neutral-800 tracking-tight">
              Execution Architecture Topology
            </span>
          </div>
          <span className="text-[10px] font-mono font-medium text-neutral-500 bg-white px-2 py-0.5 rounded border border-[#E5E7EB]">
            Route: {route}
          </span>
        </div>

        {/* ── LEVEL 1: JEV AI Decision Layer ────────────────────────────── */}
        <div className="flex flex-col items-center">
          {(() => {
            const st = getNodeStyle(jev, selectedAgentId === "jev_decision");
            return (
              <button
                type="button"
                onClick={() => onSelectAgent("jev_decision")}
                className={`w-full max-w-[280px] rounded-lg border p-2.5 transition text-left cursor-pointer ${st.border} ${st.bg} shadow-2xs hover:shadow-xs`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded-md ${st.isCompleted ? "bg-purple-100 text-purple-700" : "bg-neutral-100 text-neutral-400"}`}>
                      <BrainCircuit size={15} />
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className={`text-xs font-bold leading-tight ${st.text}`}>JEV AI</span>
                        <span className="text-[9.5px] text-neutral-400">Decision Layer</span>
                      </div>
                      <span className="text-[10px] text-neutral-500 block">
                        {jev?.status === "COMPLETED"
                          ? `Category: ${executionTrace?.jev_decision?.category || "Classified"}`
                          : "Deterministic bypass (Stage 1/2)"}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${st.badgeBg}`}>
                      {jev?.status || "SKIPPED"}
                    </span>
                    {jev?.latency_ms ? (
                      <span className="block text-[9px] text-neutral-400 font-mono mt-0.5">{jev.latency_ms}ms</span>
                    ) : null}
                  </div>
                </div>
              </button>
            );
          })()}

          {/* Connector to MARVIS */}
          <div className="my-1.5 flex flex-col items-center">
            <div className={`h-4 w-0.5 ${jev?.status === "COMPLETED" ? "bg-purple-400" : "bg-neutral-300"}`} />
            <ArrowDown size={11} className={jev?.status === "COMPLETED" ? "text-purple-500 -mt-1" : "text-neutral-400 -mt-1"} />
          </div>

          {/* ── LEVEL 2: MARVIS Router / Orchestrator ──────────────────────── */}
          {(() => {
            const st = getNodeStyle(marvis, selectedAgentId === "marvis_router");
            return (
              <button
                type="button"
                onClick={() => onSelectAgent("marvis_router")}
                className={`w-full max-w-[280px] rounded-lg border p-2.5 transition text-left cursor-pointer ${st.border} ${st.bg} shadow-2xs hover:shadow-xs`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-blue-100 text-blue-700">
                      <Layers size={15} />
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold leading-tight text-neutral-900">MARVIS Router</span>
                        <span className="text-[9.5px] text-neutral-400">Orchestrator</span>
                      </div>
                      <span className="text-[10px] text-blue-700 font-mono block">
                        {engine || "STAGE1_OR_STAGE2"}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      COMPLETED
                    </span>
                    <span className="block text-[9px] text-neutral-400 font-mono mt-0.5">
                      {marvis?.latency_ms ?? 2}ms
                    </span>
                  </div>
                </div>
              </button>
            );
          })()}

          {/* ── 3-WAY BRANCH CONNECTORS ──────────────────────────────────── */}
          <div className="relative w-full max-w-[420px] my-2">
            {/* Horizontal bus line */}
            <div className="absolute top-2 left-6 right-6 h-0.5 bg-neutral-200" />
            
            {/* Center drop line from MARVIS */}
            <div className="mx-auto w-0.5 h-2 bg-neutral-300" />

            {/* Vertical drop lines to 3 lanes */}
            <div className="grid grid-cols-3 gap-2 pt-2">
              <div className="flex flex-col items-center">
                <div className={`w-0.5 h-3 ${researcher?.status === "COMPLETED" ? "bg-cyan-500" : "bg-neutral-200"}`} />
                <ArrowDown size={10} className={researcher?.status === "COMPLETED" ? "text-cyan-600 -mt-1" : "text-neutral-300 -mt-1"} />
              </div>
              <div className="flex flex-col items-center">
                <div className={`w-0.5 h-3 ${rag?.status === "COMPLETED" ? "bg-emerald-500" : "bg-neutral-200"}`} />
                <ArrowDown size={10} className={rag?.status === "COMPLETED" ? "text-emerald-600 -mt-1" : "text-neutral-300 -mt-1"} />
              </div>
              <div className="flex flex-col items-center">
                <div className={`w-0.5 h-3 ${sandbox?.status === "COMPLETED" || coder?.status === "COMPLETED" ? "bg-amber-500" : "bg-neutral-200"}`} />
                <ArrowDown size={10} className={sandbox?.status === "COMPLETED" || coder?.status === "COMPLETED" ? "text-amber-600 -mt-1" : "text-neutral-300 -mt-1"} />
              </div>
            </div>
          </div>

          {/* ── LEVEL 3: 3 PARALLEL WORKFLOW BRANCHES ────────────────────── */}
          <div className="grid grid-cols-3 gap-2 w-full max-w-[420px]">
            {/* BRANCH 1: Researcher (Web) */}
            <div className="flex flex-col space-y-2">
              {(() => {
                const st = getNodeStyle(researcher, selectedAgentId === "researcher_agent");
                return (
                  <button
                    type="button"
                    onClick={() => onSelectAgent("researcher_agent")}
                    className={`rounded-lg border p-2 text-left transition cursor-pointer flex flex-col justify-between h-[84px] ${st.border} ${st.bg} shadow-2xs`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <Search size={13} className={st.isCompleted ? "text-cyan-600" : "text-neutral-400"} />
                        <span className={`text-[8.5px] px-1 py-0.2 rounded font-medium ${st.badgeBg}`}>
                          {researcher?.status || "SKIPPED"}
                        </span>
                      </div>
                      <span className={`text-[11px] font-bold block leading-tight ${st.text}`}>Researcher</span>
                      <span className="text-[9px] text-neutral-400 block">Tavily Web</span>
                    </div>
                    {researcher?.latency_ms ? (
                      <span className="text-[8.5px] text-neutral-400 font-mono">{researcher.latency_ms}ms</span>
                    ) : null}
                  </button>
                );
              })()}
            </div>

            {/* BRANCH 2: RAG / Document + pgvector */}
            <div className="flex flex-col space-y-1.5">
              {(() => {
                const st = getNodeStyle(rag, selectedAgentId === "rag_agent");
                return (
                  <button
                    type="button"
                    onClick={() => onSelectAgent("rag_agent")}
                    className={`rounded-lg border p-2 text-left transition cursor-pointer flex flex-col justify-between h-[42px] ${st.border} ${st.bg} shadow-2xs`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1">
                        <Database size={12} className={st.isCompleted ? "text-emerald-600" : "text-neutral-400"} />
                        <span className={`text-[10.5px] font-bold ${st.text}`}>RAG / Doc</span>
                      </div>
                      <span className={`text-[8px] px-1 py-0.2 rounded font-medium ${st.badgeBg}`}>
                        {rag?.status || "SKIPPED"}
                      </span>
                    </div>
                  </button>
                );
              })()}
              
              <div className="flex justify-center -my-1">
                <ArrowDown size={9} className={rag?.status === "COMPLETED" ? "text-emerald-500" : "text-neutral-300"} />
              </div>

              {/* Subnode: Supabase pgvector DB */}
              <div
                onClick={() => onSelectAgent("rag_agent")}
                className={`rounded border px-2 py-1 text-center transition cursor-pointer text-[9.5px] font-mono ${
                  rag?.status === "COMPLETED"
                    ? "border-emerald-300 bg-emerald-50 text-emerald-800 font-semibold"
                    : "border-neutral-200 bg-white text-neutral-400"
                }`}
              >
                pgvector (768d)
              </div>
            </div>

            {/* BRANCH 3: Coder / Analyst + AST Sandbox */}
            <div className="flex flex-col space-y-1.5">
              {(() => {
                const st = getNodeStyle(coder, selectedAgentId === "coder_agent");
                return (
                  <button
                    type="button"
                    onClick={() => onSelectAgent("coder_agent")}
                    className={`rounded-lg border p-2 text-left transition cursor-pointer flex flex-col justify-between h-[42px] ${st.border} ${st.bg} shadow-2xs`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1">
                        <Code size={12} className={st.isCompleted ? "text-indigo-600" : "text-neutral-400"} />
                        <span className={`text-[10.5px] font-bold ${st.text}`}>Coder</span>
                      </div>
                      <span className={`text-[8px] px-1 py-0.2 rounded font-medium ${st.badgeBg}`}>
                        {coder?.status || "SKIPPED"}
                      </span>
                    </div>
                  </button>
                );
              })()}

              <div className="flex justify-center -my-1">
                <ArrowDown size={9} className={sandbox?.status === "COMPLETED" ? "text-amber-500" : "text-neutral-300"} />
              </div>

              {/* Subnode: AST Sandbox */}
              {(() => {
                const st = getNodeStyle(sandbox, selectedAgentId === "ast_sandbox");
                return (
                  <button
                    type="button"
                    onClick={() => onSelectAgent("ast_sandbox")}
                    className={`rounded border px-2 py-1 text-center transition cursor-pointer text-[9.5px] font-mono flex items-center justify-center gap-1 ${
                      sandbox?.status === "COMPLETED"
                        ? "border-amber-300 bg-amber-50 text-amber-800 font-semibold"
                        : "border-neutral-200 bg-white text-neutral-400"
                    }`}
                  >
                    <Terminal size={10} />
                    <span>AST Sandbox</span>
                  </button>
                );
              })()}
            </div>
          </div>

          {/* ── CONVERGENCE CONNECTOR TO VERIFIER ─────────────────────────── */}
          <div className="relative w-full max-w-[420px] my-2">
            <div className="grid grid-cols-3 gap-2 pb-1.5">
              <div className="flex justify-center">
                <div className={`w-0.5 h-2.5 ${researcher?.status === "COMPLETED" ? "bg-cyan-500" : "bg-neutral-200"}`} />
              </div>
              <div className="flex justify-center">
                <div className={`w-0.5 h-2.5 ${rag?.status === "COMPLETED" ? "bg-emerald-500" : "bg-neutral-200"}`} />
              </div>
              <div className="flex justify-center">
                <div className={`w-0.5 h-2.5 ${sandbox?.status === "COMPLETED" ? "bg-amber-500" : "bg-neutral-200"}`} />
              </div>
            </div>
            {/* Horizontal convergence bar */}
            <div className="absolute bottom-1 left-6 right-6 h-0.5 bg-neutral-200" />
            <div className="mx-auto w-0.5 h-2 bg-neutral-300" />
            <div className="flex justify-center">
              <ArrowDown size={11} className={verifier?.status === "COMPLETED" ? "text-emerald-600 -mt-1" : "text-neutral-400 -mt-1"} />
            </div>
          </div>

          {/* ── LEVEL 4: Fact Verifier / Critic ───────────────────────────── */}
          {(() => {
            const st = getNodeStyle(verifier, selectedAgentId === "fact_verifier");
            return (
              <button
                type="button"
                onClick={() => onSelectAgent("fact_verifier")}
                className={`w-full max-w-[280px] rounded-lg border p-2.5 transition text-left cursor-pointer ${st.border} ${st.bg} shadow-2xs hover:shadow-xs`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded-md ${st.isCompleted ? "bg-emerald-100 text-emerald-700" : "bg-neutral-100 text-neutral-400"}`}>
                      <ShieldCheck size={15} />
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className={`text-xs font-bold leading-tight ${st.text}`}>Fact Verifier / Critic</span>
                      </div>
                      <span className="text-[10px] text-neutral-500 block">
                        {verifier?.status === "COMPLETED"
                          ? `Grounded claims & contradiction check`
                          : "Skipped for direct execution"}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${st.badgeBg}`}>
                      {verifier?.status || "SKIPPED"}
                    </span>
                    {verifier?.latency_ms ? (
                      <span className="block text-[9px] text-neutral-400 font-mono mt-0.5">{verifier.latency_ms}ms</span>
                    ) : null}
                  </div>
                </div>
              </button>
            );
          })()}

          {/* Connector to Synthesizer */}
          <div className="my-1.5 flex flex-col items-center">
            <div className={`h-4 w-0.5 ${synthesizer?.status === "COMPLETED" ? "bg-neutral-800" : "bg-neutral-300"}`} />
            <ArrowDown size={11} className={synthesizer?.status === "COMPLETED" ? "text-neutral-800 -mt-1" : "text-neutral-400 -mt-1"} />
          </div>

          {/* ── LEVEL 5: Synthesizer ───────────────────────────────────────── */}
          {(() => {
            const st = getNodeStyle(synthesizer, selectedAgentId === "synthesizer");
            return (
              <button
                type="button"
                onClick={() => onSelectAgent("synthesizer")}
                className={`w-full max-w-[280px] rounded-lg border p-2.5 transition text-left cursor-pointer ${st.border} ${st.bg} shadow-2xs hover:shadow-xs`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-neutral-900 text-white">
                      <Cpu size={15} />
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold leading-tight text-neutral-900">Synthesizer</span>
                      </div>
                      <span className="text-[10px] text-neutral-500 font-mono block">
                        {synthesizer?.model || "auto/claude-opus"}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      COMPLETED
                    </span>
                    <span className="block text-[9px] text-neutral-400 font-mono mt-0.5">
                      {synthesizer?.latency_ms ?? 0}ms
                    </span>
                  </div>
                </div>
              </button>
            );
          })()}

          {/* Connector to Final Answer */}
          <div className="my-1.5 flex flex-col items-center">
            <div className="h-3 w-0.5 bg-emerald-500" />
            <ArrowDown size={11} className="text-emerald-600 -mt-1" />
          </div>

          {/* ── TERMINAL: Final Answer ────────────────────────────────────── */}
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300 bg-emerald-50/70 px-3 py-1 text-xs font-semibold text-emerald-800 shadow-2xs">
            <Sparkles size={12} className="text-emerald-600" />
            <span>Final Answer Grounded &amp; Delivered</span>
          </div>
        </div>
      </div>
    </div>
  );
}
