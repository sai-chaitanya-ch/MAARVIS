import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function CodeBlock({ language, children }: { language?: string; children: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="group relative my-3 overflow-hidden rounded-xl border border-neutral-100 bg-neutral-50">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-neutral-100 bg-white px-3.5 py-2 text-[11px]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1" aria-hidden>
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-300" />
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-300" />
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-300" />
          </div>
          <span className="font-mono text-neutral-400">{language || "code"}</span>
        </div>
        <button
          type="button"
          aria-label="Copy code"
          onClick={copy}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-neutral-400 transition-all hover:bg-neutral-50 hover:text-ink"
        >
          <AnimatePresence mode="wait">
            {copied ? (
              <motion.span key="check" className="flex items-center gap-1" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <Check size={11} className="text-emerald-500" />
                <span className="text-emerald-500">Copied</span>
              </motion.span>
            ) : (
              <motion.span key="copy" className="flex items-center gap-1" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <Copy size={11} />
                Copy
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-[13px] leading-6 text-neutral-800">
        <code className="font-mono">{children}</code>
      </pre>
    </div>
  );
}
