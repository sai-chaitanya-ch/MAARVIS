import { useRef, useEffect } from "react";
import { ChatMessage } from "../lib/api";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";
import ChatComposer from "./ChatComposer";

interface ChatLayoutProps {
  messages: ChatMessage[];
  input: string;
  onInputChange: (val: string) => void;
  onSend: (text?: string) => void;
  onAttachFile?: (file: File) => Promise<any>;
  webEnabled?: boolean | null;
  onToggleWeb?: () => void;
  busy?: boolean;
  activity?: string | null;
  error?: string | null;
  attachedFileNames?: string[];
  onRemoveAttachedFile?: (index: number) => void;
  mode?: string;
  onModeChange?: (mode: any) => void;
  onOpenSettings?: (tab?: string) => void;
  onOpenAuth?: () => void;
}

export default function ChatLayout({
  messages,
  input,
  onInputChange,
  onSend,
  onAttachFile,
  webEnabled,
  onToggleWeb,
  busy = false,
  activity,
  error,
  attachedFileNames = [],
  onRemoveAttachedFile,
  mode,
  onModeChange,
  onOpenSettings,
  onOpenAuth,
}: ChatLayoutProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy, activity]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-screen w-full flex-col bg-white text-[#111111] overflow-hidden">
      {/* Scrollable Conversation Feed */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-6 pt-20 pb-36">
        <div className="mx-auto max-w-[1100px] w-full">
          {isEmpty ? (
            /* Minimal Zero State */
            <div className="flex flex-col items-center justify-center pt-24 pb-12 text-center animate-in fade-in duration-300">
              <div className="mb-4 flex items-center justify-center">
                <span className="text-2xl font-bold tracking-tight text-[#111111]">MAARVIS</span>
              </div>
              <p className="max-w-md text-sm text-[#6B7280] leading-relaxed">
                AI-powered verification and reasoning platform. Ask questions, upload documents, get verified answers.
              </p>

              {/* Minimal Suggestion Chips */}
              <div className="mt-8 flex flex-wrap justify-center gap-2 max-w-lg">
                {[
                  "What is the latest Python version?",
                  "Is 17 * 24 = 408?",
                  "Explain photosynthesis briefly.",
                  "Research recent agent architectures.",
                ].map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => onSend(prompt)}
                    className="rounded-full border border-[#E5E7EB] bg-[#F8F9FA] px-3.5 py-1.5 text-xs text-[#111111] hover:border-neutral-400 hover:bg-[#F3F4F6] transition cursor-pointer"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Message Thread */
            <div className="space-y-6">
              {messages.map((msg, idx) => {
                const isLast = idx === messages.length - 1;
                const isAssistant = msg.role === "assistant";
                const isStreaming = isLast && isAssistant && busy;

                if (msg.role === "user") {
                  return <UserMessage key={msg.id || idx} content={msg.content} />;
                }

                return (
                  <AssistantMessage
                    key={msg.id || idx}
                    message={msg}
                    isStreaming={isStreaming}
                    activeActivity={activity}
                    onRegenerate={isLast ? () => onSend(messages[idx - 1]?.content) : undefined}
                    onOpenSettings={onOpenSettings}
                  />
                );
              })}
            </div>
          )}

          {/* Error Message banner if any */}
          {error && (
            <div className="my-4 rounded-xl border border-rose-200/80 bg-rose-50/70 p-3 text-xs text-rose-800 flex items-center justify-between gap-3">
              <div>
                <p className="font-medium">Error processing request</p>
                <p className="mt-0.5 text-[11px] text-rose-700/90">{error}</p>
              </div>
              {error.toLowerCase().includes("authentication") && (
                <button
                  type="button"
                  onClick={onOpenAuth || (() => onOpenSettings?.("account"))}
                  className="shrink-0 rounded-lg bg-rose-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-950 transition cursor-pointer shadow-2xs"
                >
                  Sign In →
                </button>
              )}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* Floating Bottom Composer */}
      <ChatComposer
        input={input}
        onInputChange={onInputChange}
        onSend={onSend}
        onAttachFile={onAttachFile}
        webEnabled={webEnabled}
        onToggleWeb={onToggleWeb}
        busy={busy}
        attachedFileNames={attachedFileNames}
        onRemoveAttachedFile={onRemoveAttachedFile}
        mode={mode as any}
        onModeChange={onModeChange}
      />
    </div>
  );
}
