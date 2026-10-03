import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatMessage } from "../lib/api";
import MarkdownRenderer from "./MarkdownRenderer";
import MessageActions from "./MessageActions";
import ProcessingPipeline from "./ProcessingPipeline";
import VerificationAnalysisPanel from "./VerificationAnalysisPanel";
import SourcesDrawer from "./SourcesDrawer";

interface AssistantMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
  activeActivity?: string | null;
  onRegenerate?: () => void;
  showAnalysis?: boolean;
  showSources?: boolean;
  onToggleAnalysis?: () => void;
  onToggleSources?: () => void;
  onOpenSettings?: (tab?: string) => void;
}

export default function AssistantMessage({
  message,
  isStreaming = false,
  activeActivity,
  onRegenerate,
  onOpenSettings,
}: AssistantMessageProps) {
  const [showVerificationPanel, setShowVerificationPanel] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      return params.has("analysis") || params.has("evidence") || params.has("agents");
    }
    return false;
  });
  const [showSources, setShowSources] = useState(false);

  const hasAnswer = Boolean(message.content && message.content.trim().length > 0);
  const isProcessing = isStreaming || (!hasAnswer && (message.events?.length || 0) > 0);

  // Derive verification status
  const rawStatus = String(message.verification?.status || "").toLowerCase();
  const decisionLabel = String(message.verification?.decision || "").toUpperCase();
  const conflictingCount =
    message.verification?.conflicting_claims ??
    message.verification?.conflictingClaims ??
    message.verification?.claims_summary?.conflicting ??
    message.verification?.contradicted ??
    0;

  const isConflicting = rawStatus === "conflicting" || decisionLabel === "CONFLICTING" || conflictingCount > 0;
  const isPartiallyVerified =
    rawStatus === "partially_verified" ||
    rawStatus === "partial" ||
    decisionLabel === "PARTIALLY VERIFIED" ||
    (message.verification?.metrics?.partiallyVerified != null &&
      message.verification.metrics.partiallyVerified > 0);

  const isMath = Boolean(
    (message.verification as any)?.is_math === true ||
    (message.verification as any)?.is_math === "true" ||
    decisionLabel === "SANDBOX VERIFIED" ||
    message.verification?.note?.toLowerCase().includes("deterministic")
  );

  // Subtle Verification Note text & styling
  let verificationNote: string | null = null;
  let noteColorClass = "text-[#6B7280]";

  if (hasAnswer && !isProcessing) {
    const isDirect =
      message.routing?.route === "DIRECT_FAST" ||
      rawStatus === "direct_answer" ||
      decisionLabel === "DIRECT ANSWER" ||
      message.verification?.performed === false ||
      (message.claims?.length === 0 && (message.sources?.length ?? 0) === 0 && !isMath);

    if (isDirect) {
      verificationNote = null;
    } else if (isMath || decisionLabel === "SANDBOX VERIFIED") {
      verificationNote = "✓ Verified via deterministic AST Sandbox execution.";
      noteColorClass = "text-emerald-700/90";
    } else if (decisionLabel === "MULTI-SOURCE VERIFIED") {
      verificationNote = "✓ Supported by uploaded documents and external sources.";
      noteColorClass = "text-emerald-700/90";
    } else if (decisionLabel === "SUPPORTED BY DOCUMENT") {
      verificationNote = "✓ Supported by uploaded document.";
      noteColorClass = "text-blue-700/90";
    } else if (decisionLabel === "SUPPORTED BY EXTERNAL SOURCES") {
      verificationNote = "✓ Supported by external sources.";
      noteColorClass = "text-cyan-700/90";
    } else if (decisionLabel === "NOT VERIFIED") {
      verificationNote = "⚠ Independent verification unavailable. Answer is based on model knowledge only.";
      noteColorClass = "text-neutral-600";
    } else if (isConflicting) {
      verificationNote =
        "⚠ Verification note: Sources contain conflicting information. Review the evidence before relying on this answer.";
      noteColorClass = "text-orange-700/90";
    } else if (isPartiallyVerified) {
      verificationNote = "◐ Some claims independently supported by retrieved sources.";
      noteColorClass = "text-amber-700/90";
    } else if (rawStatus === "verified" || decisionLabel === "VERIFIED") {
      verificationNote = "✓ All extracted claims independently verified against retrieved sources.";
      noteColorClass = "text-emerald-700/90";
    }
  }

  return (
    <div className="flex w-full flex-col items-start py-3 text-[#111111] relative">
      {/* Brand Header */}
      <div className="mb-2 flex items-center gap-1.5">
        <span className="text-xs font-bold tracking-tight text-neutral-900">MAARVIS</span>
      </div>

      {/* Temporary Processing Pipeline: Visually collapses and unmounts once the answer is ready */}
      <AnimatePresence>
        {isProcessing && (
          <motion.div
            key="processing-panel"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0, marginTop: 0, marginBottom: 0 }}
            transition={{ duration: 0.35, ease: "easeInOut" }}
            className="w-full overflow-hidden mb-3"
          >
            <ProcessingPipeline
              events={message.events || []}
              activeActivity={activeActivity}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Answer Area: Rendered with clean typography */}
      {hasAnswer && !isProcessing && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="w-full text-[15px] leading-relaxed text-[#111111]"
        >
          {/* Clean Markdown Typography */}
          <div className="prose prose-neutral max-w-none text-[#111111] prose-p:leading-relaxed prose-pre:bg-neutral-50 prose-pre:border prose-pre:border-[#E5E7EB]">
            <MarkdownRenderer content={message.content} />
          </div>

          {/* Subtle Verification Note directly attached to this response */}
          {verificationNote && (
            <div className={`mt-3 mb-1 flex items-center gap-1.5 text-xs font-normal select-none ${noteColorClass}`}>
              <span>{verificationNote}</span>
            </div>
          )}

          {/* Action Row with [ Copy ] [ Like ] [ Dislike ] [ Share ] [ Regenerate ] [ More ] [ ✓ Verification ] */}
          {!isStreaming && (
            <MessageActions
              content={message.content}
              verification={message.verification}
              sources={message.sources}
              isVerifying={isProcessing}
              onOpenVerification={() => setShowVerificationPanel(true)}
              onOpenSources={() => setShowSources(true)}
              onRegenerate={onRegenerate}
            />
          )}
        </motion.div>
      )}

      {/* Per-Message Floating Verification Analysis Panel */}
      {showVerificationPanel && (
        <VerificationAnalysisPanel
          verification={message.verification}
          sources={message.sources}
          claims={message.claims}
          executionTrace={message.execution_trace || (message.verification as any)?.execution_trace}
          executionId={message.execution_id || (message.verification as any)?.execution_id}
          capabilities={message.capabilities || message.execution_trace?.capabilities}
          recommendations={message.recommendations || message.execution_trace?.recommendations}
          onOpenSettings={onOpenSettings}
          onClose={() => setShowVerificationPanel(false)}
        />
      )}

      {/* Sources Drawer / Modal */}
      {showSources && (
        <SourcesDrawer
          sources={message.sources || []}
          onClose={() => setShowSources(false)}
        />
      )}
    </div>
  );
}
