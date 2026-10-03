import { FormEvent, useRef, KeyboardEvent } from "react";
import { Paperclip, Globe, Code2, Mic, ArrowUp } from "lucide-react";

interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onAttach: (file: File) => void;
  onToggleWeb: () => void;
  webEnabled: boolean | null;
  busy: boolean;
  autoFocus?: boolean;
  isLanding?: boolean;
}

export default function ChatInput({
  value,
  onChange,
  onSend,
  onAttach,
  onToggleWeb,
  webEnabled,
  busy,
  autoFocus,
  isLanding = false,
}: ChatInputProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!busy && value.trim()) onSend();
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!busy && value.trim()) onSend();
    }
  };

  const hasText = Boolean(value.trim());

  return (
    <form onSubmit={submit} className="relative w-full">
      <div
        className={`relative w-full rounded-[24px] bg-white transition-all ${
          isLanding
            ? "shadow-[0_18px_60px_-15px_rgba(195,215,245,0.65),_0_0_0_1px_rgba(0,0,0,0.04)] hover:shadow-[0_22px_70px_-12px_rgba(190,210,245,0.75)]"
            : "border border-neutral-200/80 shadow-[0_10px_35px_-8px_rgba(0,0,0,0.08)]"
        }`}
      >
        {/* Hidden file input */}
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          accept=".pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.webp"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onAttach(file);
            e.target.value = "";
          }}
        />

        {/* Text Area */}
        <textarea
          ref={textRef}
          value={value}
          autoFocus={autoFocus}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask anything..."
          rows={1}
          aria-label="Ask anything input"
          className="w-full resize-none bg-transparent px-5 pb-11 pt-4 text-[15px] leading-relaxed text-neutral-800 outline-none placeholder:text-neutral-400/90"
        />

        {/* Bottom Toolbar */}
        <div className="absolute inset-x-3 bottom-2.5 flex items-center justify-between pointer-events-none">
          {/* Left action icons */}
          <div className="flex items-center gap-1.5 pointer-events-auto">
            <button
              type="button"
              title="Attach file"
              aria-label="Attach file"
              onClick={() => fileRef.current?.click()}
              className="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            >
              <Paperclip size={18} strokeWidth={1.8} />
            </button>

            <button
              type="button"
              title={webEnabled ? "Web search enabled" : "Toggle web search"}
              aria-label="Toggle web search"
              onClick={onToggleWeb}
              className={`rounded-lg p-1.5 transition-colors ${
                webEnabled
                  ? "bg-blue-50 text-blue-600 hover:bg-blue-100"
                  : "text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
              }`}
            >
              <Globe size={18} strokeWidth={1.8} />
            </button>

            <button
              type="button"
              title="Code mode"
              aria-label="Code mode"
              className="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            >
              <Code2 size={18} strokeWidth={1.8} />
            </button>
          </div>

          {/* Right action icons */}
          <div className="flex items-center gap-2 pointer-events-auto pr-1">
            {!isLanding && (
              <button
                type="button"
                title="Voice input"
                aria-label="Voice input"
                className="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
              >
                <Mic size={18} strokeWidth={1.8} />
              </button>
            )}

            <button
              type="submit"
              disabled={busy || !hasText}
              aria-label="Send query"
              className={`flex h-9 w-9 items-center justify-center rounded-full transition-all ${
                hasText && !busy
                  ? "bg-neutral-900 text-white hover:bg-black shadow-xs scale-100"
                  : "bg-neutral-300 text-white cursor-not-allowed opacity-80"
              }`}
            >
              <ArrowUp size={18} strokeWidth={2.4} />
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
