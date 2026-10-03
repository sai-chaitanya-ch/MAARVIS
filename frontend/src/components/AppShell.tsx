import { ReactNode } from "react";
import { Sun, Sparkles, BookOpen } from "lucide-react";

export type NavTab = "assistant" | "knowledge";

export default function AppShell({
  children,
  onLogo,
  activeTab = "assistant",
  onTabChange,
}: {
  children: ReactNode;
  onLogo: () => void;
  activeTab?: NavTab;
  onTabChange?: (tab: NavTab) => void;
}) {
  return (
    <div className="min-h-screen bg-[#FBFBFC] text-[#111111]">
      {/* Header */}
      <header className="fixed left-0 top-0 z-30 flex w-full items-center justify-between px-6 py-3.5 sm:px-10 bg-white/80 backdrop-blur-md border-b border-neutral-100/80">
        {/* Left: Pure Typography Logo */}
        <div className="flex items-center gap-8">
          <button
            onClick={onLogo}
            className="flex items-center gap-0.5 text-xl tracking-tight transition-opacity hover:opacity-80"
            aria-label="MAARVIS home"
          >
            <span className="font-bold tracking-tight text-neutral-900">MAARVIS</span>
          </button>

          {/* Navigation Tabs */}
          {onTabChange && (
            <nav className="flex items-center gap-1 rounded-full bg-neutral-100/80 p-1 border border-neutral-200/50">
              <button
                type="button"
                onClick={() => onTabChange("assistant")}
                className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-all ${
                  activeTab === "assistant"
                    ? "bg-white text-neutral-900 shadow-2xs font-semibold"
                    : "text-neutral-500 hover:text-neutral-800"
                }`}
              >
                <Sparkles size={13} className={activeTab === "assistant" ? "text-neutral-900" : "text-neutral-400"} />
                <span>Verify Assistant</span>
              </button>

              <button
                type="button"
                onClick={() => onTabChange("knowledge")}
                className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-all ${
                  activeTab === "knowledge"
                    ? "bg-white text-neutral-900 shadow-2xs font-semibold"
                    : "text-neutral-500 hover:text-neutral-800"
                }`}
              >
                <BookOpen size={13} className={activeTab === "knowledge" ? "text-emerald-600" : "text-neutral-400"} />
                <span>Knowledge Agent</span>
                <span className="rounded-full bg-emerald-50 px-1.5 py-0.2 text-[9.5px] font-bold text-emerald-600 border border-emerald-200/60">
                  RAG
                </span>
              </button>
            </nav>
          )}
        </div>

        {/* Right: Theme Toggle & Avatar */}
        <div className="flex items-center gap-4">
          <button
            type="button"
            aria-label="Toggle theme"
            className="rounded-full p-1.5 text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            <Sun size={20} strokeWidth={1.7} />
          </button>

          <div
            className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-100 border border-neutral-200 text-[13.5px] font-medium text-neutral-700 shadow-xs select-none"
            title="User Account"
          >
            A
          </div>
        </div>
      </header>

      <main className="relative min-h-screen pt-16">{children}</main>
    </div>
  );
}
