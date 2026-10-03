import { Zap, Bot, MessageSquare } from "lucide-react";

export type MarvisMode = "AUTO" | "MULTI_AGENT" | "DIRECT";

interface ModeOption {
  value: MarvisMode;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const OPTIONS: ModeOption[] = [
  { value: "AUTO", label: "Auto", icon: <Zap size={13} strokeWidth={2} />, description: "Smart routing" },
  { value: "MULTI_AGENT", label: "Multi-Agent", icon: <Bot size={13} strokeWidth={2} />, description: "Full verification" },
  { value: "DIRECT", label: "Direct Fast", icon: <MessageSquare size={13} strokeWidth={2} />, description: "Skip verification" },
];

interface MarvisModeSelector {
  mode: MarvisMode;
  onChange: (mode: MarvisMode) => void;
  attachedCount?: number;
  disabled?: boolean;
}

export default function MarvisModeSelector({ mode, onChange, attachedCount = 0, disabled = false }: MarvisModeSelector) {
  // Show attachment escalation indicator
  const showRagBadge = mode === "AUTO" && attachedCount > 0;

  return (
    <div className="flex items-center gap-1">
      <div className="flex items-center rounded-full border border-[#E5E7EB] bg-[#F8F9FA] p-0.5 gap-0.5">
        {OPTIONS.map((opt) => {
          const isActive = mode === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              title={opt.description}
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11.5px] font-medium transition-all ${
                isActive
                  ? "bg-white text-[#111111] shadow-sm border border-[#E5E7EB]"
                  : "text-[#6B7280] hover:text-[#111111] hover:bg-white/60"
              } disabled:opacity-40 disabled:cursor-not-allowed`}
              aria-pressed={isActive}
            >
              {opt.icon}
              {opt.label}
            </button>
          );
        })}
      </div>
      {showRagBadge && (
        <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-100 px-2 py-0.5 text-[10.5px] font-medium text-blue-700">
          <Bot size={11} />
          RAG Active
        </span>
      )}
    </div>
  );
}
