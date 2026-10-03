import { Check, AlertTriangle, CircleDashed, ShieldAlert } from "lucide-react";
import { Verification } from "../lib/api";

interface VerificationBadgeProps {
  verification?: Verification;
  onClick?: () => void;
}

export default function VerificationBadge({ verification, onClick }: VerificationBadgeProps) {
  if (!verification || !verification.performed) {
    return null;
  }

  const isIncomplete =
    verification.status === "verification_incomplete" ||
    verification.independentVerificationCompleted === false ||
    verification.independent_verification_completed === false;

  const status = String(verification.status || "").toLowerCase();
  const metrics = verification.metrics;
  const verifiedPct = metrics?.verified ?? (verification.score != null ? Math.round(verification.score * 100) : null);

  let label = "Not Verified";
  let icon = <CircleDashed size={12} className="text-[#9CA3AF]" />;
  let pillStyle = "bg-[#F8F9FA] text-[#6B7280] border-[#E5E7EB] hover:bg-[#F3F4F6]";

  if (isIncomplete) {
    label = "Verification Incomplete";
    icon = <AlertTriangle size={12} className="text-amber-600" />;
    pillStyle = "bg-amber-50/70 text-amber-800 border-amber-200/60 hover:bg-amber-100/70";
  } else if (status === "conflicting" || (metrics?.conflicting != null && metrics.conflicting > 0)) {
    const conflictPct = metrics?.conflicting ?? 20;
    label = `Conflicting Evidence ${conflictPct}%`;
    icon = <ShieldAlert size={12} className="text-rose-600" />;
    pillStyle = "bg-rose-50/60 text-rose-800 border-rose-200/60 hover:bg-rose-100/60";
  } else if (status === "verified" || verifiedPct === 100) {
    label = verifiedPct != null ? `Verified ${verifiedPct}%` : "Verified";
    icon = <Check size={11} strokeWidth={2.5} className="text-emerald-700" />;
    pillStyle = "bg-emerald-50/70 text-emerald-800 border-emerald-200/60 hover:bg-emerald-100/70";
  } else if (status === "partially_verified" || (verifiedPct != null && verifiedPct > 0)) {
    label = verifiedPct != null ? `Partially Verified ${verifiedPct}%` : "Partially Verified";
    icon = (
      <span className="flex h-3 w-3 items-center justify-center text-[10px] text-neutral-600 font-bold">
        ◐
      </span>
    );
    pillStyle = "bg-neutral-100/80 text-neutral-700 border-neutral-200/80 hover:bg-neutral-200/70";
  } else {
    label = "Not Verified";
    icon = <CircleDashed size={12} className="text-[#9CA3AF]" />;
    pillStyle = "bg-[#F8F9FA] text-[#6B7280] border-[#E5E7EB] hover:bg-[#F3F4F6]";
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition cursor-pointer select-none ${pillStyle}`}
      title="View Evidence Metrics"
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
