import { useState } from "react";
import {
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  Share2,
  RotateCcw,
  MoreHorizontal,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldCheck,
} from "lucide-react";
import { Verification, Source } from "../lib/api";

interface MessageActionsProps {
  content: string;
  verification?: Verification;
  sources?: Source[];
  isVerifying?: boolean;
  onOpenVerification?: () => void;
  onOpenSources?: () => void;
  onRegenerate?: () => void;
}

export default function MessageActions({
  content,
  verification,
  sources = [],
  isVerifying = false,
  onOpenVerification,
  onOpenSources,
  onRegenerate,
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState<boolean | null>(null);
  const [showMoreMenu, setShowMoreMenu] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ text: content, title: "MAARVIS response" });
      } catch {
        // ignore
      }
    } else {
      handleCopy();
    }
  };

  // Check if math query
  const isMath = Boolean(
    (verification as any)?.is_math === true ||
    (verification as any)?.is_math === "true" ||
    (verification as any)?.task_type === "math" ||
    verification?.note?.toLowerCase().includes("math") ||
    verification?.note?.toLowerCase().includes("calculation") ||
    verification?.note?.toLowerCase().includes("deterministic")
  );

  const rawStatus = String(verification?.status || "").toLowerCase();
  const conflictingCount =
    verification?.conflicting_claims ??
    verification?.conflictingClaims ??
    verification?.claims_summary?.conflicting ??
    verification?.contradicted ??
    0;

  let vState = isMath
    ? {
        icon: <CheckCircle2 size={12} className="text-emerald-600" />,
        label: "Verified 100%",
        badgeClass: "text-emerald-700 bg-emerald-50/80 border-emerald-200 hover:bg-emerald-100/60",
      }
    : {
        icon: <span className="text-amber-600 font-bold text-xs">◐</span>,
        label: "Partially Verified",
        badgeClass: "text-amber-700 bg-amber-50/80 border-amber-200 hover:bg-amber-100/60",
      };

  const decisionUpper = String((verification as any)?.decision || "").toUpperCase();

  if (isVerifying) {
    vState = {
      icon: <span className="text-sky-600 animate-spin text-xs">◌</span>,
      label: "Verifying...",
      badgeClass: "text-sky-700 bg-sky-50/80 border-sky-200",
    };
  } else if (rawStatus === "not_evaluated" || decisionUpper === "NOT EVALUATED" || rawStatus === "direct_answer" || decisionUpper === "DIRECT ANSWER") {
    vState = {
      icon: <span className="text-neutral-400 font-bold text-xs">—</span>,
      label: "Not Evaluated",
      badgeClass: "text-neutral-600 bg-neutral-50 border-neutral-200 hover:bg-neutral-100",
    };
  } else if (rawStatus === "unverified" || decisionUpper === "NOT VERIFIED") {
    vState = {
      icon: <span className="text-neutral-500 text-xs">⚠</span>,
      label: "Not Verified",
      badgeClass: "text-neutral-600 bg-neutral-100 border-neutral-200 hover:bg-neutral-200/60",
    };
  } else if (rawStatus === "conflicting" || conflictingCount > 0) {
    vState = {
      icon: <AlertTriangle size={12} className="text-orange-600" />,
      label: "Conflicting",
      badgeClass: "text-orange-700 bg-orange-50/80 border-orange-200 hover:bg-orange-100/60",
    };
  } else if (rawStatus === "rejected") {
    vState = {
      icon: <XCircle size={12} className="text-red-600" />,
      label: "Rejected",
      badgeClass: "text-red-700 bg-red-50/80 border-red-200 hover:bg-red-100/60",
    };
  } else if (rawStatus === "verified" || decisionUpper.includes("VERIFIED")) {
    vState = {
      icon: <CheckCircle2 size={12} className="text-emerald-600" />,
      label: "Verified",
      badgeClass: "text-emerald-700 bg-emerald-50/80 border-emerald-200 hover:bg-emerald-100/60",
    };
  }

  return (
    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 pt-2 text-[#6B7280]">
      {/* Action Row: Copy, Like, Dislike, Share, Regenerate, More, Verification */}
      <div className="flex flex-wrap items-center gap-1">
        {/* Copy */}
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
          title="Copy answer"
        >
          {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>

        {/* Like */}
        <button
          type="button"
          onClick={() => setLiked(liked === true ? null : true)}
          className={`rounded-md p-1.5 text-xs transition hover:bg-[#F3F4F6] cursor-pointer ${
            liked === true ? "text-neutral-900 bg-[#F3F4F6]" : "hover:text-[#111111]"
          }`}
          title="Helpful"
        >
          <ThumbsUp size={12} />
        </button>

        {/* Dislike */}
        <button
          type="button"
          onClick={() => setLiked(liked === false ? null : false)}
          className={`rounded-md p-1.5 text-xs transition hover:bg-[#F3F4F6] cursor-pointer ${
            liked === false ? "text-neutral-900 bg-[#F3F4F6]" : "hover:text-[#111111]"
          }`}
          title="Unhelpful"
        >
          <ThumbsDown size={12} />
        </button>

        {/* Share */}
        <button
          type="button"
          onClick={handleShare}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
          title="Share"
        >
          <Share2 size={12} />
          <span>Share</span>
        </button>

        {/* Regenerate */}
        {onRegenerate && (
          <button
            type="button"
            onClick={onRegenerate}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
            title="Regenerate answer"
          >
            <RotateCcw size={12} />
            <span>Regenerate</span>
          </button>
        )}

        {/* More */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowMoreMenu(!showMoreMenu)}
            className="rounded-md p-1.5 text-xs hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
            title="More options"
          >
            <MoreHorizontal size={12} />
          </button>

          {showMoreMenu && (
            <div className="absolute left-0 bottom-full mb-1 z-30 w-36 rounded-lg border border-[#E5E7EB] bg-white py-1 shadow-lg text-xs">
              <button
                type="button"
                onClick={() => {
                  handleCopy();
                  setShowMoreMenu(false);
                }}
                className="w-full text-left px-3 py-1.5 hover:bg-[#F8F9FA] text-[#374151]"
              >
                Copy text
              </button>
              {sources.length > 0 && onOpenSources && (
                <button
                  type="button"
                  onClick={() => {
                    onOpenSources();
                    setShowMoreMenu(false);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#F8F9FA] text-[#374151]"
                >
                  View {sources.length} sources
                </button>
              )}
            </div>
          )}
        </div>

        {/* END ACTION: Verification Button */}
        {onOpenVerification && (
          <button
            type="button"
            onClick={onOpenVerification}
            className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium transition cursor-pointer shadow-2xs ml-1 ${vState.badgeClass}`}
            title="View verification analysis"
          >
            {vState.icon}
            <span>{vState.label}</span>
          </button>
        )}
      </div>
    </div>
  );
}
