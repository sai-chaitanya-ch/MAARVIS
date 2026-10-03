import { X, ExternalLink, FileText, Globe, Calculator, Terminal } from "lucide-react";
import { Source } from "../lib/api";

interface SourcesDrawerProps {
  sources: Source[];
  onClose: () => void;
}

export default function SourcesDrawer({ sources, onClose }: SourcesDrawerProps) {
  const getIcon = (type?: string) => {
    switch (type) {
      case "document":
        return <FileText size={13} className="text-[#6B7280]" />;
      case "calculation":
        return <Calculator size={13} className="text-[#6B7280]" />;
      case "code_execution":
        return <Terminal size={13} className="text-[#6B7280]" />;
      default:
        return <Globe size={13} className="text-[#6B7280]" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-[1px] p-4">
      <div className="w-full max-w-md rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-lg text-[#111111] animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-[#111111]">Sources ({sources.length})</h3>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#111111] transition"
            aria-label="Close sources"
          >
            <X size={15} />
          </button>
        </div>

        {/* Source List */}
        <div className="mt-3.5 max-h-80 overflow-y-auto space-y-2 pr-1">
          {sources.length === 0 ? (
            <p className="text-xs text-[#9CA3AF] py-6 text-center">No primary sources attached.</p>
          ) : (
            sources.map((src, idx) => {
              const numStr = String(idx + 1).padStart(2, "0");
              return (
                <div
                  key={src.id || idx}
                  className="group flex items-start gap-3 rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-3 text-xs hover:border-neutral-300 hover:bg-[#F3F4F6] transition"
                >
                  <span className="font-mono text-[11px] font-semibold text-[#9CA3AF] pt-0.5">
                    {numStr}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      {getIcon(src.source_type)}
                      <p className="font-medium text-[#111111] truncate">
                        {src.title || src.domain || "Primary Source"}
                      </p>
                    </div>
                    {src.evidence && (
                      <p className="mt-1 line-clamp-2 text-[11px] text-[#6B7280] leading-relaxed">
                        {src.evidence}
                      </p>
                    )}
                    {src.url && (
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1.5 inline-flex items-center gap-1 text-[10.5px] font-medium text-neutral-600 hover:text-neutral-900 transition"
                      >
                        <span className="truncate max-w-[260px]">{src.domain || src.url}</span>
                        <ExternalLink size={10} className="shrink-0" />
                      </a>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="mt-4 flex justify-end border-t border-[#E5E7EB] pt-3">
          <button
            onClick={onClose}
            className="rounded-lg bg-neutral-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
