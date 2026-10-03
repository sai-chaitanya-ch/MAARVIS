import { Verification } from "../lib/api";

const STATUS_LABEL: Record<string, string> = {
  VERIFIED: "Verified",
  PARTIALLY_VERIFIED: "Partially verified",
  CONTRADICTED: "Conflicting sources",
  INSUFFICIENT_EVIDENCE: "Insufficient evidence",
  ERROR: "Error",
};

export default function VerificationChart({ verification }: { verification: Verification }) {
  const supported = verification.supported ?? 0;
  const partial = verification.partial ?? 0;
  const unverified = verification.unverified ?? 0;
  const contradicted = verification.contradicted ?? 0;
  const total = Math.max(supported + partial + unverified + contradicted, 1);
  const pct = verification.score != null ? Math.round(verification.score * 100) : null;

  // Calculate donut chart percentages
  const s1 = (supported / total) * 100;
  const s2 = (partial / total) * 100;
  const s3 = (unverified / total) * 100;
  const s4 = (contradicted / total) * 100;

  // Conic gradient: emerald=supported, blue=partial, gray=unverified, orange=contradicted
  const gradient = `conic-gradient(
    #10b981 0% ${s1}%,
    #93c5fd ${s1}% ${s1 + s2}%,
    #e5e7eb ${s1 + s2}% ${s1 + s2 + s3}%,
    #f97316 ${s1 + s2 + s3}% 100%
  )`;

  const statusLabel = STATUS_LABEL[verification.status ?? ""] ?? "Checking…";

  return (
    <div className="flex items-center gap-5">
      {/* Donut */}
      <div
        className="relative h-[72px] w-[72px] flex-shrink-0 rounded-full"
        style={{ background: gradient }}
        aria-hidden
      >
        <div className="absolute inset-[10px] flex flex-col items-center justify-center rounded-full bg-white">
          <span className="text-[13px] font-semibold text-ink">
            {pct != null ? `${pct}%` : "—"}
          </span>
        </div>
      </div>

      {/* Labels */}
      <div className="space-y-1">
        <p className="text-[13px] font-medium text-ink">{statusLabel}</p>
        <div className="flex flex-col gap-0.5 text-[11px]">
          <span className="flex items-center gap-1.5 text-emerald-600">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
            Verified
          </span>
          <span className="flex items-center gap-1.5 text-blue-500">
            <span className="inline-block h-2 w-2 rounded-full bg-blue-300" />
            Partial
          </span>
          {(unverified + contradicted) > 0 && (
            <span className="flex items-center gap-1.5 text-neutral-400">
              <span className="inline-block h-2 w-2 rounded-full bg-neutral-300" />
              Unverified / Conflicted
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
