import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink } from "lucide-react";
import { ClaimResult, Source, Verification } from "../lib/api";
import VerificationChart from "./VerificationChart";
import ClaimList from "./ClaimList";

export default function MobileVerificationSheet({
  id,
  verification,
  claims,
  sources,
  onClose,
}: {
  id: string;
  verification: Verification;
  claims: ClaimResult[];
  sources: Source[];
  onClose: () => void;
}) {
  const urlSources = sources.filter((s) => s.url);

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Sheet */}
      <motion.div
        key="sheet"
        id={id}
        role="dialog"
        aria-label="Verification Analysis"
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 30, stiffness: 380 }}
        className="fixed bottom-0 inset-x-0 z-50 max-h-[80vh] overflow-y-auto rounded-t-2xl bg-white shadow-2xl"
      >
        {/* Handle */}
        <div className="mx-auto my-3 h-1 w-10 rounded-full bg-neutral-200" />

        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-50 px-4 py-3">
          <p className="text-[13px] font-semibold text-ink">Verification Analysis</p>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="inline-flex h-7 w-7 items-center justify-center rounded-full text-neutral-400 hover:bg-neutral-50"
          >
            <X size={14} />
          </button>
        </div>

        <div className="p-4 space-y-4 pb-8">
          <VerificationChart verification={verification} />

          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-xl bg-neutral-50 p-3 text-[12px]">
            <span className="text-neutral-500">Claims checked</span>
            <span className="text-right font-medium text-ink">{verification.claims_checked ?? 0}</span>
            <span className="text-neutral-500">Supported</span>
            <span className="text-right font-medium text-emerald-600">{verification.supported ?? 0}</span>
            <span className="text-neutral-500">Partially supported</span>
            <span className="text-right font-medium text-blue-500">{verification.partial ?? 0}</span>
            <span className="text-neutral-500">Unverified</span>
            <span className="text-right font-medium text-neutral-400">{verification.unverified ?? 0}</span>
          </div>

          {urlSources.length > 0 && (
            <div>
              <p className="mb-2 text-[12px] font-semibold text-ink">Sources</p>
              <ul className="space-y-2">
                {urlSources.slice(0, 6).map((s) => (
                  <li key={s.id} className="flex items-center justify-between gap-2 rounded-lg border border-neutral-50 bg-neutral-50 px-3 py-2">
                    <span className="truncate text-[12px] text-neutral-600">{s.title || s.domain}</span>
                    <a href={s.url!} target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-accent flex-shrink-0">
                      Open <ExternalLink size={10} />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {claims.length > 0 && (
            <div>
              <p className="mb-2 text-[12px] font-semibold text-ink">Claims</p>
              <ClaimList claims={claims} />
            </div>
          )}

          {verification.note && (
            <p className="rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-[11.5px] leading-5 text-amber-700">
              {verification.note}
            </p>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
