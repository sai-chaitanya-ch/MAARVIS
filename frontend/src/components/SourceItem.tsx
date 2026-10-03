import { ExternalLink, FileText, Globe } from "lucide-react";
import { Source } from "../lib/api";

export default function SourceItem({ source }: { source: Source }) {
  const isDoc = source.source_type === "document";
  const isCalc = source.source_type === "calculation" || source.source_type === "code_execution";

  if (isCalc) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-neutral-100 bg-neutral-50 px-2.5 py-1 text-[11.5px] text-neutral-500">
        <FileText size={11} />
        {source.title}
      </span>
    );
  }

  if (isDoc) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-neutral-100 bg-neutral-50 px-2.5 py-1 text-[11.5px] text-neutral-500">
        <FileText size={11} />
        {source.title || "Document"}
      </span>
    );
  }

  if (!source.url) return null;

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1.5 rounded-full border border-neutral-100 bg-neutral-50 px-2.5 py-1 text-[11.5px] text-neutral-500 transition-colors hover:border-accent/30 hover:text-accent"
    >
      <Globe size={11} />
      <span className="max-w-[140px] truncate">{source.domain || source.title}</span>
      <ExternalLink size={10} className="flex-shrink-0" />
    </a>
  );
}
