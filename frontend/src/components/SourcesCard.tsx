import { X, ExternalLink, FileText, Globe } from "lucide-react";
import { Source } from "../lib/api";

interface SourcesCardProps {
  sources?: Source[];
  onClose?: () => void;
  className?: string;
}

export default function SourcesCard({
  sources = [],
  onClose,
  className = "",
}: SourcesCardProps) {
  const displaySources = sources;

  // Helper to render authentic icon badges for popular domains
  const renderSourceIcon = (source: Source, index: number) => {
    const url = source.url?.toLowerCase() || "";
    const title = source.title?.toLowerCase() || "";

    if (url.includes("python.org") || title.includes("python release")) {
      return (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-50 border border-blue-100/80">
          <svg className="h-4 w-4" viewBox="0 0 128 128">
            <path
              fill="#3776AB"
              d="M63.8 2c-15.6 0-25 6.7-25 19.8v14.5h25.4v3.6H26.3c-13.3 0-24.3 8-24.3 23.4s9.7 23.4 23 23.4h7.5V76.3c0-13.8 11.7-25 25.5-25h25.4V36.7c0-14.7-12-25.5-25.5-25.5H63.8z"
            />
            <path
              fill="#FFD43B"
              d="M64.2 126c15.6 0 25-6.7 25-19.8V91.7H63.8v-3.6h37.9c13.3 0 24.3-8 24.3-23.4s-9.7-23.4-23-23.4h-7.5v10.4c0 13.8-11.7 25-25.5 25H44.6v14.6c0 14.7 12 25.5 25.5 25.5h-5.9z"
            />
          </svg>
        </div>
      );
    }

    if (url.includes("docs.python.org") || index === 1) {
      return (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
          <FileText size={15} />
        </div>
      );
    }

    if (url.includes("realpython.com") || index === 2) {
      return (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#DE3C26] text-white shadow-xs">
          <span className="text-[11px] font-black tracking-tighter">RP</span>
        </div>
      );
    }

    return (
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-neutral-100 text-neutral-500">
        <Globe size={14} />
      </div>
    );
  };

  return (
    <div
      className={`relative w-[340px] sm:w-[380px] rounded-2xl border border-neutral-100/90 bg-white p-5 shadow-[0_12px_36px_-6px_rgba(0,0,0,0.09),_0_0_0_1px_rgba(0,0,0,0.03)] text-neutral-800 transition-all ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3">
        <h3 className="text-[15px] font-bold tracking-tight text-neutral-900">
          Sources
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-full p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            aria-label="Close sources panel"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Sources list */}
      {displaySources.length === 0 ? (
        <p className="py-4 text-center text-[12.5px] text-neutral-400">
          No external sources cited for this response.
        </p>
      ) : (
        <div className="mt-1 flex flex-col divide-y divide-neutral-100">
          {displaySources.map((source, idx) => (
          <a
            key={source.id || idx}
            href={source.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center justify-between py-3 transition-colors hover:bg-neutral-50/70 -mx-2 px-2 rounded-xl"
          >
            <div className="flex items-center gap-3 min-w-0 pr-2">
              {/* Index Number */}
              <span className="w-3 text-center text-[12px] font-medium text-neutral-400">
                {idx + 1}
              </span>

              {/* Favicon / Icon */}
              {renderSourceIcon(source, idx)}

              {/* Title & Domain */}
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium text-neutral-900 group-hover:text-blue-600 transition-colors">
                  {source.title || source.domain || "Web Source"}
                </p>
                <p className="truncate text-[11px] text-neutral-400 font-mono">
                  {source.url || source.domain || ""}
                </p>
              </div>
            </div>

            {/* External link button */}
            <div className="shrink-0 text-neutral-400 group-hover:text-neutral-700 transition-colors">
              <ExternalLink size={13} strokeWidth={1.8} />
            </div>
          </a>
        ))}
        </div>
      )}
    </div>
  );
}
