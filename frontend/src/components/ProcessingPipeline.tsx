import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { AgentEvent } from "../lib/api";

export interface PipelineStepDef {
  id: string;
  label: string;
  tool: string;
  status: "pending" | "active" | "completed";
}

interface ProcessingPipelineProps {
  events: AgentEvent[];
  isDocument?: boolean;
  isWeb?: boolean;
  isMath?: boolean;
  isCode?: boolean;
  activeActivity?: string | null;
}

export function determineSteps(
  events: AgentEvent[],
  isDocument?: boolean,
  isWeb?: boolean,
  isMath?: boolean,
  isCode?: boolean
): PipelineStepDef[] {
  const eventNames = new Set(events.map((e) => e.event));
  const activeEvent = events.length > 0 ? events[events.length - 1] : null;
  const isEventDone = (name: string) =>
    events.some((e) => e.event === name && e.status === "completed");
  const isEventActive = (name: string) =>
    activeEvent?.event === name && activeEvent?.status === "started";

  let baseSteps: { id: string; label: string; tool: string }[] = [];

  if (isMath || eventNames.has("calculation")) {
    baseSteps = [
      { id: "routing", label: "Understand", tool: "Math Parser" },
      { id: "calculation", label: "Calculate", tool: "Deterministic" },
      { id: "verification", label: "Verify", tool: "Verification Agent" },
      { id: "finalization", label: "Answer", tool: "MAARVIS" },
    ];
  } else if (isCode || eventNames.has("code_execution")) {
    baseSteps = [
      { id: "routing", label: "Understand", tool: "Qwen3-Coder" },
      { id: "code_execution", label: "Sandbox", tool: "Code Sandbox" },
      { id: "verification", label: "Verify", tool: "Verification Agent" },
      { id: "finalization", label: "Answer", tool: "MAARVIS" },
    ];
  } else if (isDocument || eventNames.has("retrieval")) {
    baseSteps = [
      { id: "routing", label: "Understand", tool: "Doc Parser" },
      { id: "retrieval", label: "Evidence", tool: "BGE-M3" },
      { id: "reranking", label: "Rerank", tool: "BGE Reranker" },
      { id: "verification", label: "Verify", tool: "Verification Agent" },
      { id: "finalization", label: "Answer", tool: "Qwen3" },
    ];
  } else if (isWeb || eventNames.has("web_search")) {
    baseSteps = [
      { id: "routing", label: "Understand", tool: "Qwen3" },
      { id: "web_search", label: "Search", tool: "Tavily Search" },
      { id: "retrieval", label: "Evidence", tool: "BGE-M3" },
      { id: "reranking", label: "Rerank", tool: "BGE Reranker" },
      { id: "verification", label: "Verify", tool: "Verification Agent" },
      { id: "finalization", label: "Answer", tool: "Qwen3" },
    ];
  } else {
    // General / Factual Question: strictly Understand -> Evidence -> Verify -> Answer (NEVER Generate before Verify)
    baseSteps = [
      { id: "routing", label: "Understand", tool: "Qwen3" },
      { id: "web_search", label: "Search", tool: "Tavily Search" },
      { id: "retrieval", label: "Evidence", tool: "BGE-M3" },
      { id: "verification", label: "Verify", tool: "Verification Agent" },
      { id: "finalization", label: "Answer", tool: "Qwen3" },
    ];
  }

  let foundActive = false;
  return baseSteps.map((step) => {
    let status: "pending" | "active" | "completed" = "pending";
    if (isEventDone(step.id)) {
      status = "completed";
    } else if (isEventActive(step.id) || (!foundActive && !isEventDone(step.id))) {
      status = "active";
      foundActive = true;
    }
    return { ...step, status };
  });
}

function getHeaderInfo(steps: PipelineStepDef[], activeActivity?: string | null) {
  const activeStep = steps.find((s) => s.status === "active");
  if (!activeStep) {
    return {
      title: "Analyzing your question...",
      subtitle: "Using multiple AI models and verification tools",
    };
  }
  switch (activeStep.label) {
    case "Understand":
      return {
        title: "Analyzing your question...",
        subtitle: "Using Qwen3 to understand intent and query structure",
      };
    case "Search":
      return {
        title: "Searching primary sources...",
        subtitle: "Retrieving real-time web references via Tavily Search",
      };
    case "Calculate":
      return {
        title: "Deterministic calculation...",
        subtitle: "Evaluating mathematical operations without hallucination",
      };
    case "Sandbox":
      return {
        title: "Executing code sandbox...",
        subtitle: "Running isolated code test execution in container sandbox",
      };
    case "Evidence":
      return {
        title: "Retrieving evidence passages...",
        subtitle: "Dense semantic grounding using BGE-M3 embedding",
      };
    case "Rerank":
      return {
        title: "Cross-scoring evidence...",
        subtitle: "Evaluating passage relevance with BGE Reranker",
      };
    case "Verify":
      return {
        title: "Verifying claims independently...",
        subtitle: "Fact-checking claims against primary evidence and checking conflicts",
      };
    case "Answer":
      return {
        title: "Synthesizing verified answer...",
        subtitle: "Generating verified response with Qwen3",
      };
    default:
      return {
        title: activeActivity || "Processing verification pipeline...",
        subtitle: "Using multiple AI models and verification tools",
      };
  }
}

export default function ProcessingPipeline({
  events,
  isDocument,
  isWeb,
  isMath,
  isCode,
  activeActivity,
}: ProcessingPipelineProps) {
  const steps = determineSteps(events, isDocument, isWeb, isMath, isCode);
  const header = getHeaderInfo(steps, activeActivity);

  return (
    <div className="w-full max-w-2xl rounded-2xl border border-[#E5E7EB] bg-[#F8F9FA]/80 p-5 sm:p-6 text-[#111111] transition-all">
      {/* Centered Minimal Header */}
      <div className="flex flex-col items-center text-center mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neutral-400 opacity-60"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-neutral-800"></span>
          </span>
          <h4 className="text-xs font-semibold tracking-tight text-[#111111]">
            {header.title}
          </h4>
        </div>
        <p className="text-[11px] text-[#6B7280]">
          {header.subtitle}
        </p>
      </div>

      {/* Horizontal Connected Step Line */}
      <div className="flex items-center justify-between w-full px-2 sm:px-4">
        {steps.map((step, idx) => {
          const isCompleted = step.status === "completed";
          const isActive = step.status === "active";

          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              {/* Step Node */}
              <div className="flex flex-col items-center text-center relative group min-w-[56px] sm:min-w-[68px]">
                {/* Circle Icon */}
                <div className="flex items-center justify-center h-6 w-6 mb-1.5">
                  {isCompleted ? (
                    <motion.div
                      initial={{ scale: 0.8 }}
                      animate={{ scale: 1 }}
                      className="flex h-5 w-5 items-center justify-center rounded-full bg-neutral-900 text-white shadow-2xs"
                    >
                      <Check size={11} strokeWidth={2.6} />
                    </motion.div>
                  ) : isActive ? (
                    <div className="relative flex h-5 w-5 items-center justify-center">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neutral-400 opacity-40"></span>
                      <div className="flex h-5 w-5 items-center justify-center rounded-full border-[1.5px] border-neutral-900 bg-white shadow-2xs">
                        <div className="h-2 w-2 rounded-full bg-neutral-900 animate-pulse" />
                      </div>
                    </div>
                  ) : (
                    <div className="h-4 w-4 rounded-full border border-[#D1D5DB] bg-white" />
                  )}
                </div>

                {/* Stage Name */}
                <span
                  className={`text-[11.5px] tracking-tight leading-tight ${
                    isActive
                      ? "text-neutral-900 font-semibold"
                      : isCompleted
                      ? "text-neutral-800 font-medium"
                      : "text-neutral-400 font-normal"
                  }`}
                >
                  {step.label}
                </span>

                {/* Model / Tool Name */}
                <span className="text-[10px] text-[#9CA3AF] leading-tight mt-0.5 truncate max-w-[70px] sm:max-w-[85px]">
                  {step.tool}
                </span>
              </div>

              {/* Connecting Line between steps */}
              {idx < steps.length - 1 && (
                <div className="flex-1 mx-1 sm:mx-2 h-[1px] bg-neutral-200 relative -top-3">
                  <motion.div
                    className="h-full bg-neutral-800"
                    initial={{ width: 0 }}
                    animate={{ width: isCompleted ? "100%" : "0%" }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
