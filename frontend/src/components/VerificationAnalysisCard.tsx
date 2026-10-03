import { X, CheckCircle2, AlertTriangle } from "lucide-react";
import { Verification } from "../lib/api";

interface VerificationAnalysisCardProps {
  verification?: Verification;
  score?: number; // e.g. 0.92 or 0.60
  verifiedPct?: number; // e.g. 92 or 40
  partialPct?: number; // e.g. 6 or 60
  unverifiedPct?: number; // e.g. 2 or 0
  conflictingPct?: number; // e.g. 0
  note?: string;
  onClose?: () => void;
  className?: string;
}

export default function VerificationAnalysisCard({
  verification,
  score,
  verifiedPct,
  partialPct,
  unverifiedPct,
  conflictingPct,
  note,
  onClose,
  className = "",
}: VerificationAnalysisCardProps) {
  // Calculate real percentages from verification object
  const totalClaims =
    (verification?.supported ?? 0) +
    (verification?.partial ?? 0) +
    (verification?.unverified ?? 0) +
    (verification?.contradicted ?? 0);

  let vPct: number;
  let pPct: number;
  let uPct: number;
  let cPct: number;

  if (verifiedPct != null) {
    vPct = verifiedPct;
    pPct = partialPct ?? 0;
    uPct = unverifiedPct ?? 0;
    cPct = conflictingPct ?? 0;
  } else if (totalClaims > 0) {
    vPct = Math.round(((verification?.supported ?? 0) / totalClaims) * 100);
    pPct = Math.round(((verification?.partial ?? 0) / totalClaims) * 100);
    uPct = Math.round(((verification?.unverified ?? 0) / totalClaims) * 100);
    cPct = Math.round(((verification?.contradicted ?? 0) / totalClaims) * 100);
  } else if (verification?.score != null) {
    const s = Math.round(verification.score * 100);
    vPct = s;
    pPct = Math.max(0, 100 - s);
    uPct = 0;
    cPct = 0;
  } else {
    vPct = 0;
    pPct = 0;
    uPct = 0;
    cPct = 0;
  }

  const calcScore = score ?? verification?.score ?? (vPct / 100);
  const isPartiallyVerified =
    calcScore < 0.8 || verification?.status === "PARTIALLY_VERIFIED";

  const mainPct =
    verification?.score != null
      ? Math.round(verification.score * 100)
      : isPartiallyVerified
      ? pPct
      : vPct;
  const mainLabel = isPartiallyVerified ? "Partially Verified" : "Verified";

  // SVG Donut metrics
  const radius = 46;
  const circumference = 2 * Math.PI * radius; // ~289.02

  const strokeWidth = 11;
  const center = 60;

  // Segment stroke dashes
  const vDash = (vPct / 100) * circumference;
  const pDash = (pPct / 100) * circumference;
  const uDash = (uPct / 100) * circumference;
  const cDash = (cPct / 100) * circumference;

  // Offsets
  const vOffset = 0;
  const pOffset = -vDash;
  const uOffset = -(vDash + pDash);
  const cOffset = -(vDash + pDash + uDash);

  return (
    <div
      className={`relative w-[340px] sm:w-[380px] rounded-2xl border border-neutral-100/90 bg-white p-5 shadow-[0_12px_36px_-6px_rgba(0,0,0,0.09),_0_0_0_1px_rgba(0,0,0,0.03)] text-neutral-800 transition-all ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3">
        <h3 className="text-[15px] font-bold tracking-tight text-neutral-900">
          Verification Analysis
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-full p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            aria-label="Close verification analysis"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Donut Chart & Legend */}
      <div className="mt-2 flex items-center justify-between gap-4">
        {/* SVG Donut */}
        <div className="relative flex h-[120px] w-[120px] shrink-0 items-center justify-center">
          <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 120 120">
            {/* Background ring */}
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke="#F1F5F9"
              strokeWidth={strokeWidth}
            />

            {/* Verified Segment (Emerald Green) */}
            {vPct > 0 && (
              <circle
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke="#10B981"
                strokeWidth={strokeWidth}
                strokeDasharray={`${vDash} ${circumference}`}
                strokeDashoffset={vOffset}
                strokeLinecap="butt"
              />
            )}

            {/* Partially Verified Segment (Sky Blue or Yellow/Amber) */}
            {pPct > 0 && (
              <circle
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={isPartiallyVerified ? "#F59E0B" : "#38BDF8"}
                strokeWidth={strokeWidth}
                strokeDasharray={`${pDash} ${circumference}`}
                strokeDashoffset={pOffset}
                strokeLinecap="butt"
              />
            )}

            {/* Unverified Segment (Coral / Pink) */}
            {uPct > 0 && (
              <circle
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke="#F87171"
                strokeWidth={strokeWidth}
                strokeDasharray={`${uDash} ${circumference}`}
                strokeDashoffset={uOffset}
                strokeLinecap="butt"
              />
            )}

            {/* Conflicting Segment (Slate Gray) */}
            {cPct > 0 && (
              <circle
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke="#94A3B8"
                strokeWidth={strokeWidth}
                strokeDasharray={`${cDash} ${circumference}`}
                strokeDashoffset={cOffset}
                strokeLinecap="butt"
              />
            )}
          </svg>

          {/* Center Text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <span className="text-[26px] font-bold leading-tight tracking-tight text-neutral-900">
              {mainPct}%
            </span>
            <span
              className={`text-[11px] font-medium leading-none ${
                isPartiallyVerified ? "text-amber-500" : "text-neutral-500"
              }`}
            >
              {mainLabel}
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-col gap-2 text-[12.5px] font-normal text-neutral-600">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#10B981]" />
            <span>Verified ({vPct}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                isPartiallyVerified ? "bg-[#F59E0B]" : "bg-[#38BDF8]"
              }`}
            />
            <span>Partially Verified ({pPct}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#F87171]" />
            <span>Unverified ({uPct}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#94A3B8]" />
            <span>Conflicting ({cPct}%)</span>
          </div>
        </div>
      </div>

      {/* Status Summary Banner */}
      <div className="mt-4">
        {isPartiallyVerified ? (
          <div className="flex items-start gap-2.5 rounded-xl border border-amber-100 bg-[#FFF8E6] p-3">
            <div className="mt-0.5 shrink-0 text-amber-500">
              <AlertTriangle size={16} className="fill-amber-500 text-white" />
            </div>
            <p className="text-[12px] font-medium leading-snug text-[#92400E]">
              {note ||
                "Parts of this answer are not fully verified. The topic is debated and depends on definition and context."}
            </p>
          </div>
        ) : (
          <div className="flex items-start gap-2.5 rounded-xl border border-emerald-100 bg-[#EDF8F1] p-3">
            <div className="mt-0.5 shrink-0 text-emerald-600">
              <CheckCircle2 size={16} className="fill-emerald-600 text-white" />
            </div>
            <p className="text-[12px] font-medium leading-snug text-[#166534]">
              {note ||
                "Our system verified most of the information using multiple reliable sources."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
