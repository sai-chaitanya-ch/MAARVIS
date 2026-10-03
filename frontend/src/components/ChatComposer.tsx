import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { Plus, ArrowUp, Mic, Globe, X, FileText } from "lucide-react";
import MarvisModeSelector, { type MarvisMode } from "./MarvisModeSelector";


interface ChatComposerProps {
  input: string;
  onInputChange: (val: string) => void;
  onSend: (text?: string) => void;
  onAttachFile?: (file: File) => Promise<any>;
  webEnabled?: boolean | null;
  onToggleWeb?: () => void;
  busy?: boolean;
  attachedFileNames?: string[];
  onRemoveAttachedFile?: (index: number) => void;
  mode?: MarvisMode;
  onModeChange?: (mode: MarvisMode) => void;
}

export default function ChatComposer({
  input,
  onInputChange,
  onSend,
  onAttachFile,
  webEnabled,
  onToggleWeb,
  busy = false,
  attachedFileNames = [],
  onRemoveAttachedFile,
  mode,
  onModeChange,
}: ChatComposerProps) {
  const [isRecording, setIsRecording] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !busy) {
        onSend();
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0 && onAttachFile) {
      for (let i = 0; i < files.length; i++) {
        await onAttachFile(files[i]);
      }
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleVoiceToggle = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }
    if (isRecording) {
      setIsRecording(false);
      return;
    }
    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-US";
      recognition.onstart = () => setIsRecording(true);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        onInputChange((input ? input + " " : "") + transcript);
        setIsRecording(false);
      };
      recognition.onerror = () => setIsRecording(false);
      recognition.onend = () => setIsRecording(false);
      recognition.start();
    } catch {
      setIsRecording(false);
    }
  };

  const canSend = Boolean(input.trim()) && !busy;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 bg-gradient-to-t from-white via-white/95 to-transparent pb-6 pt-4 px-4 sm:px-6">
      <div className="mx-auto max-w-3xl">
        {/* Attached Files Chips */}
        {attachedFileNames.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5 px-2">
            {attachedFileNames.map((name, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-full border border-[#E5E7EB] bg-[#F8F9FA] px-2.5 py-0.5 text-xs text-[#111111]"
              >
                <FileText size={12} className="text-[#6B7280]" />
                <span className="truncate max-w-[180px]">{name}</span>
                {onRemoveAttachedFile && (
                  <button
                    type="button"
                    onClick={() => onRemoveAttachedFile(idx)}
                    className="rounded-full p-0.5 text-[#9CA3AF] hover:text-[#111111]"
                  >
                    <X size={11} />
                  </button>
                )}
              </span>
            ))}
          </div>
        )}

        {/* MARVIS Mode Selector */}
        {onModeChange && (
          <div className="mb-2 px-1">
            <MarvisModeSelector
              mode={mode ?? "AUTO"}
              onChange={onModeChange}
              attachedCount={attachedFileNames?.length ?? 0}
              disabled={busy}
            />
          </div>
        )}

        {/* Rounded Input Container */}
        <div className="relative flex flex-col rounded-2xl border border-[#E5E7EB] bg-[#FFFFFF] shadow-sm transition-all focus-within:border-blue-400 focus-within:shadow-[0_0_0_3px_rgba(59,130,246,0.15)] focus-within:ring-0">
          {/* Main Input Row */}
          <div className="flex items-end px-3 py-2.5 gap-2">
            {/* Attachment Button */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={handleFileChange}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111] transition"
              title="Attach documents (PDF, DOCX, TXT)"
              disabled={busy}
            >
              <Plus size={18} strokeWidth={2} />
            </button>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything..."
              rows={1}
              disabled={busy}
              className="flex-1 max-h-44 resize-none bg-transparent py-1 text-[15px] leading-relaxed text-[#111111] placeholder:text-[#9CA3AF] focus:outline-none disabled:opacity-50"
            />

            {/* Right Action Icons */}
            <div className="flex items-center gap-1">
              {/* Optional Web Search Toggle */}
              {onToggleWeb && (
                <button
                  type="button"
                  onClick={onToggleWeb}
                  className={`flex h-8 w-8 items-center justify-center rounded-full transition ${
                    webEnabled
                      ? "bg-neutral-900 text-white"
                      : "text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#111111]"
                  }`}
                  title={webEnabled ? "Web search enabled" : "Enable web search"}
                >
                  <Globe size={15} />
                </button>
              )}

              {/* Voice Input */}
              <button
                type="button"
                onClick={handleVoiceToggle}
                className={`flex h-8 w-8 items-center justify-center rounded-full transition ${
                  isRecording
                    ? "bg-rose-50 text-rose-600 animate-pulse"
                    : "text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#111111]"
                }`}
                title="Voice input"
                disabled={busy}
              >
                <Mic size={16} />
              </button>

              {/* Send Button */}
              <button
                type="button"
                onClick={() => onSend()}
                disabled={!canSend}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-white transition hover:bg-neutral-800 disabled:opacity-20 disabled:hover:bg-neutral-900"
                aria-label="Send message"
              >
                <ArrowUp size={16} strokeWidth={2.5} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
