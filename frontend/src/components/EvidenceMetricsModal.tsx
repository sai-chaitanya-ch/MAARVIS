import { X, AlertTriangle, ShieldCheck, HelpCircle } from "lucide-react";
import { Verification } from "../lib/api";

interface EvidenceMetricsModalProps {
  verification?: Verification;
  sourcesCount?: number;
  onClose: () => void;
}

export default function EvidenceMetricsModal({
  verification,
  sourcesCount = 0,
  onClose,
}: EvidenceMetricsModalProps) {
  const isIncomplete =
    verification?.status === "verification_incomplete" ||
    verification?.independentVerificationCompleted === false ||
    verification?.independent_verification_completed === false;

  const isConflicting =
    verification?.status === "conflicting" ||
    (verification?.metrics?.conflicting != null && verification.metrics.conflicting > 0);

  const isUnverified = verification?.status === "unverified";

  const metrics = verification?.metrics;
  const verifiedStr = isIncomplete || metrics?.verified == null ? "—" : `${metrics.verified}%`;
  const partialStr = isIncomplete || metrics?.partiallyVerified == null ? "—" : `${metrics.partiallyVerified}%`;
  const unverifiedStr = isIncomplete || metrics?.unverified == null ? "—" : `${metrics.unverified}%`;
  const conflictingStr = isIncomplete || metrics?.conflicting == null ? "—" : `${metrics.conflicting}%`;

  const totalClaims =
    verification?.totalClaims ??
    verification?.total_claims ??
    verification?.claims_checked ??
    0;

  const primarySources = Math.max(0, sourcesCount > 0 ? sourcesCount - 1 : 0);
  const independentChecks = verification?.verificationMethods?.length || (totalClaims > 0 ? 1 : 0);
  const iterations = verification?.iterations || 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-[1px] p-4">
      <div className="w-full max-w-sm rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-lg text-[#111111] animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-neutral-700" />
            <h3 className="text-sm font-semibold text-[#111111]">Evidence Metrics</h3>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#111111] transition"
            aria-label="Close modal"
          >
            <X size={15} />
          </button>
        </div>

        {/* Warning / Incomplete banners */}
        {isIncomplete && (
          <div className="mt-3.5 flex items-start gap-2 rounded-lg bg-neutral-50 border border-neutral-200 p-2.5 text-xs text-neutral-700">
            <AlertTriangle size={14} className="shrink-0 text-amber-600 mt-0.5" />
            <div>
              <p className="font-medium text-neutral-800">Verification Incomplete</p>
              <p className="text-[11px] text-neutral-500 mt-0.5">
                Independent verification could not be completed.
              </p>
            </div>
          </div>
        )}

        {isConflicting && !isIncomplete && (
          <div className="mt-3.5 flex items-start gap-2 rounded-lg bg-amber-50/70 border border-amber-200/60 p-2.5 text-xs text-amber-900">
            <AlertTriangle size={14} className="shrink-0 text-amber-600 mt-0.5" />
            <div>
              <p className="font-medium">Conflicting evidence detected</p>
              <p className="text-[11px] text-amber-700 mt-0.5">
                Some independent sources provide conflicting statements.
              </p>
            </div>
          </div>
        )}

        {isUnverified && !isIncomplete && (
          <div className="mt-3.5 flex items-start gap-2 rounded-lg bg-neutral-50 border border-neutral-200 p-2.5 text-xs text-neutral-700">
            <HelpCircle size={14} className="shrink-0 text-neutral-500 mt-0.5" />
            <div>
              <p className="font-medium text-neutral-800">Not independently verified</p>
              <p className="text-[11px] text-neutral-500 mt-0.5">
                Claims could not be supported by sufficient independent evidence.
              </p>
            </div>
          </div>
        )}

        {/* Breakdown table */}
        <div className="mt-4 space-y-2 text-xs">
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Verified</span>
            <span className="font-medium text-[#111111]">{verifiedStr}</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Partially Verified</span>
            <span className="font-medium text-[#111111]">{partialStr}</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Unverified</span>
            <span className="font-medium text-[#111111]">{unverifiedStr}</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Conflicting</span>
            <span className="font-medium text-[#111111]">{conflictingStr}</span>
          </div>
        </div>

        {/* Divider */}
        <div className="my-3.5 border-t border-[#E5E7EB]" />

        {/* Counts */}
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Claims Checked</span>
            <span className="font-medium text-[#111111]">{totalClaims}</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Sources Used</span>
            <span className="font-medium text-[#111111]">{sourcesCount}</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Primary Sources</span>
            <span className="font-medium text-[#111111]">{primarySources}</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Independent Checks</span>
            <span className="font-medium text-[#111111]">{independentChecks}</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[#6B7280]">Verification Iterations</span>
            <span className="font-medium text-[#111111]">{iterations}</span>
          </div>
        </div>

        {/* Note if present */}
        {verification?.note && (
          <p className="mt-3.5 rounded-lg bg-[#F8F9FA] p-2 text-[11px] text-[#6B7280] leading-relaxed border border-[#E5E7EB]">
            {verification.note}
          </p>
        )}

        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg bg-neutral-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 transition"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
