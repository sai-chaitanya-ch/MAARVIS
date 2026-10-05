import { Sliders, Plus, History, MessageSquare, Key, LogIn } from "lucide-react";
import type { User } from "@supabase/supabase-js";

export type NavTab = "assistant" | "evaluation";

interface HeaderProps {
  activeTab?: NavTab;
  onTabChange?: (tab: NavTab) => void;
  onNewChat: () => void;
  onOpenHistory?: () => void;
  onOpenSettings?: () => void;
  onOpenProviders?: () => void;
  user?: User | null;
  onOpenAuth?: () => void;
  onOpenAccount?: () => void;
}

export default function Header({
  activeTab = "assistant",
  onTabChange,
  onNewChat,
  onOpenHistory,
  onOpenSettings,
  onOpenProviders,
  user,
  onOpenAuth,
  onOpenAccount,
}: HeaderProps) {
  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : null;

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
          className="flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-medium text-[#111111] hover:bg-[#F3F4F6] transition shadow-2xs cursor-pointer"
          title="New Chat"
        >
          <Plus size={13} />
          <span className="hidden sm:inline">New</span>
        </button>

        {onOpenHistory && (
          <button
            type="button"
            onClick={onOpenHistory}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
            title="Conversation history"
          >
            <History size={16} />
          </button>
        )}

        {onOpenProviders && (
          <button
            type="button"
            onClick={onOpenProviders}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
            title="API & Providers"
          >
            <Key size={16} />
          </button>
        )}

        {onOpenSettings && (
          <button
            type="button"
            onClick={onOpenSettings}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
            title="Settings"
          >
            <Sliders size={16} />
          </button>
        )}

        {/* User Account / Auth Button */}
        {user ? (
          <button
            type="button"
            onClick={onOpenAccount || onOpenSettings}
            className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-900 border border-neutral-700 text-xs font-bold text-white select-none hover:opacity-85 transition cursor-pointer"
            title={`Signed in as ${user.email} (Click for Account settings)`}
          >
            {userInitial || "U"}
          </button>
        ) : (
          <button
            type="button"
            onClick={onOpenAuth || onOpenAccount || onOpenSettings}
            className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-900 bg-neutral-900 px-2.5 py-1 text-xs font-medium text-white hover:bg-neutral-800 transition shadow-2xs cursor-pointer"
            title="Sign In with Supabase"
          >
            <LogIn size={13} />
            <span className="hidden sm:inline">Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
}
