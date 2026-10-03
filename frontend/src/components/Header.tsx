import { Sliders, Plus, History, MessageSquare, Key } from "lucide-react";

export type NavTab = "assistant" | "evaluation";

interface HeaderProps {
  activeTab?: NavTab;
  onTabChange?: (tab: NavTab) => void;
  onNewChat: () => void;
  onOpenHistory?: () => void;
  onOpenSettings?: () => void;
  onOpenProviders?: () => void;
}

export default function Header({
  activeTab = "assistant",
  onTabChange,
  onNewChat,
  onOpenHistory,
  onOpenSettings,
  onOpenProviders,
}: HeaderProps) {
  return (
    <header className="fixed left-0 top-0 z-30 flex h-14 w-full items-center justify-between border-b border-[#E5E7EB] bg-white/90 px-6 backdrop-blur-md">
      {/* Left: Wordmark & Mode Tabs */}
      <div className="flex items-center gap-6">
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-0.5 text-lg font-semibold tracking-tight text-[#111111] hover:opacity-80 transition cursor-pointer select-none"
        >
          <span className="font-bold tracking-tight">MAARVIS</span>
        </button>

        {onTabChange && (
          <div className="flex items-center rounded-lg border border-[#E5E7EB] bg-[#F8F9FA] p-0.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => onTabChange("assistant")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 transition cursor-pointer ${
                activeTab === "assistant"
                  ? "bg-white text-[#111111] shadow-2xs font-semibold"
                  : "text-[#6B7280] hover:text-[#111111]"
              }`}
            >
              <MessageSquare size={13} />
              <span>Assistant</span>
            </button>
          </div>
        )}
      </div>

      {/* Right: Header Actions */}
      <div className="flex items-center gap-2">

        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-medium text-[#111111] hover:bg-[#F3F4F6] transition shadow-2xs"
          title="New Chat"
        >
          <Plus size={13} />
          <span className="hidden sm:inline">New</span>
        </button>


        {onOpenHistory && (
          <button
            type="button"
            onClick={onOpenHistory}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111] transition"
            title="Conversation history"
          >
            <History size={16} />
          </button>
        )}

        {onOpenProviders && (
          <button
            type="button"
            onClick={onOpenProviders}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111] transition"
            title="API & Providers"
          >
            <Key size={16} />
          </button>
        )}

        {onOpenSettings && (
          <button
            type="button"
            onClick={onOpenSettings}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111] transition"
            title="Settings"
          >
            <Sliders size={16} />
          </button>
        )}

        {/* Minimal User Avatar */}
        <div
          className="flex h-7 w-7 items-center justify-center rounded-full bg-[#F3F4F6] border border-[#E5E7EB] text-xs font-medium text-[#111111] select-none"
          title="Account"
        >
          A
        </div>
      </div>
    </header>
  );
}
