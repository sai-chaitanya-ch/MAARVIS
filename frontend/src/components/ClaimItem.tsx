import { ClaimResult } from "../lib/api";

const STATUS_CONFIG: Record<string, { symbol: string; className: string }> = {
  SUPPORTED: { symbol: "✓", className: "text-emerald-600" },
  PARTIALLY_SUPPORTED: { symbol: "~", className: "text-blue-500" },
  CONTRADICTED: { symbol: "✕", className: "text-orange-500" },
  INSUFFICIENT_EVIDENCE: { symbol: "?", className: "text-neutral-400" },
  UNVERIFIABLE: { symbol: "—", className: "text-neutral-400" },
};

export default function ClaimItem({ claim }: { claim: ClaimResult }) {
  const cfg = STATUS_CONFIG[claim.status] ?? { symbol: "?", className: "text-neutral-400" };
  return (
    <li className="flex items-start gap-2 rounded-lg bg-neutral-50 px-2.5 py-2">
      <span className={`mt-0.5 flex-shrink-0 text-[13px] font-semibold ${cfg.className}`} aria-hidden>
        {cfg.symbol}
      </span>
      <p className="text-[11.5px] leading-4 text-neutral-600">{claim.claim_text}</p>
    </li>
  );
}
