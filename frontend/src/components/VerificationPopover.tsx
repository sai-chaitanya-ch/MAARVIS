import { motion } from "framer-motion";
import { X, ExternalLink } from "lucide-react";
import { ClaimResult, Source, Verification } from "../lib/api";
import VerificationChart from "./VerificationChart";
import ClaimList from "./ClaimList";

interface Props {
  id: string;
  verification: Verification;
  claims: ClaimResult[];
  sources: Source[];
  onClose: () => void;
}

export default function VerificationPopover({ id, verification, claims, sources, onClose }: Props) {
  const urlSources = sources.filter((s) => s.url);

  return (
    <motion.div
      id={id}
      role="dialog"
      aria-label="Verification Analysis"
      initial={{ opacity: 0, scale: 0.96, y: -4 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96, y: -4 }}
      transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
      className="absolute left-0 top-10 z-40 w-[340px] rounded-2xl border border-neutral-100 bg-white shadow-[0_20px_60px_-20px_rgba(0,0,0,0.22),0_0_0_1px_rgba(0,0,0,0.04)]"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-50 px-4 py-3">
        <p className="text-[13px] font-semibold text-ink">Verification Analysis</p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close verification panel"
          className="inline-flex h-6 w-6 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-50 hover:text-ink"
        >
          <X size={13} />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Donut chart */}
        <VerificationChart verification={verification} />

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-xl bg-neutral-50 p-3 text-[12px]">
          <span className="text-neutral-500">Claims checked</span>
          <span className="text-right font-medium text-ink">{verification.claims_checked ?? 0}</span>
          <span className="text-neutral-500">Supported</span>
          <span className="text-right font-medium text-emerald-600">{verification.supported ?? 0}</span>
          <span className="text-neutral-500">Partially supported</span>
          <span className="text-right font-medium text-blue-500">{verification.partial ?? 0}</span>
          <span className="text-neutral-500">Unverified</span>
          <span className="text-right font-medium text-neutral-400">{verification.unverified ?? 0}</span>
          {(verification.contradicted ?? 0) > 0 && (
            <>
              <span className="text-neutral-500">Contradicted</span>
              <span className="text-right font-medium text-orange-500">{verification.contradicted}</span>
            </>
          )}
        </div>

        {/* Sources */}
        {urlSources.length > 0 && (
          <div>
            <p className="mb-2 text-[12px] font-semibold text-ink">Sources</p>
            <ul className="space-y-1.5">
              {urlSources.slice(0, 5).map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-2 rounded-lg border border-neutral-50 bg-neutral-50 px-2.5 py-1.5">
                  <span className="truncate text-[11.5px] text-neutral-600 max-w-[200px]">
                    {s.title || s.domain}
                  </span>
                  <a
                    href={s.url!}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] text-accent hover:text-blue-600 flex-shrink-0"
                    aria-label={`Open ${s.title}`}
                  >
                    Open <ExternalLink size={10} />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Claims */}
        {claims.length > 0 && (
          <div>
            <p className="mb-2 text-[12px] font-semibold text-ink">Claims</p>
            <ClaimList claims={claims} />
          </div>
        )}

        {/* Verification note */}
        {verification.note && (
          <p className="rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-[11.5px] leading-5 text-amber-700">
            {verification.note}
          </p>
        )}
      </div>
    </motion.div>
  );
}
