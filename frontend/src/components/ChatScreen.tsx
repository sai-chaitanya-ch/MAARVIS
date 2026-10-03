import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatMessage } from "../lib/api";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";
import ChatInput from "./ChatInput";
import VerificationAnalysisCard from "./VerificationAnalysisCard";
import SourcesCard from "./SourcesCard";
import ErrorMessage from "./ErrorMessage";

interface ChatScreenProps {
  messages: ChatMessage[];
  input: string;
  onInput: (v: string) => void;
  onSend: () => void;
  onAttach: (file: File) => void;
  onToggleWeb: () => void;
  webEnabled: boolean | null;
  busy: boolean;
  error: string | null;
}

export default function ChatScreen({
  messages,
  input,
  onInput,
  onSend,
  onAttach,
  onToggleWeb,
  webEnabled,
  busy,
  error,
}: ChatScreenProps) {
  // Track open inspection panels by message index or id
  // By default in Image 1, message 0 has both Verification and Sources open,
  // and message 1 has Verification open.
  const [activePanels, setActivePanels] = useState<{
    [msgId: string]: { analysis: boolean; sources: boolean };
  }>({});

  const endRef = useRef<HTMLDivElement>(null);

  // Initialize panels for assistant messages based on actual data
  useEffect(() => {
    if (messages.length > 0) {
      setActivePanels((prev) => {
        const next = { ...prev };
        messages.forEach((msg) => {
          if (msg.role === "assistant" && !next[msg.id]) {
            const hasSources = Boolean(msg.sources && msg.sources.length > 0);
            const hasVerif = Boolean(msg.verification?.performed);
            next[msg.id] = {
              analysis: hasVerif,
              sources: hasSources,
            };
          }
        });
        return next;
      });
    }
  }, [messages]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, messages[messages.length - 1]?.content?.length]);

  const toggleAnalysis = (id: string) => {
    setActivePanels((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        analysis: !prev[id]?.analysis,
      },
    }));
  };

  const toggleSources = (id: string) => {
    setActivePanels((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        sources: !prev[id]?.sources,
      },
    }));
  };

  return (
    <div className="relative min-h-[calc(100vh-4rem)] w-full pb-36">
      {/* Main Chat Container inside a spacious layout */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <div className="rounded-3xl border border-neutral-100/80 bg-white p-5 sm:p-8 shadow-[0_4px_24px_rgba(0,0,0,0.02)]">
          {error && <ErrorMessage message={error} />}

          {/* Conversation Thread & Side Inspection Panels */}
          <div className="space-y-10">
            {messages.map((message, idx) => {
              if (message.role === "user") {
                return (
                  <div key={message.id || idx} className="w-full">
                    <UserMessage content={message.content} />
                  </div>
                );
              }

              const panelState = activePanels[message.id] ?? {
                analysis: Boolean(message.verification?.performed),
                sources: Boolean(message.sources && message.sources.length > 0),
              };

              return (
                <div
                  key={message.id || idx}
                  className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-start"
                >
                  {/* Assistant Message Bubble / Content (Left Column) */}
                  <div className="lg:col-span-7">
                    <AssistantMessage
                      message={message}
                      showAnalysis={panelState.analysis}
                      showSources={panelState.sources}
                      onToggleAnalysis={() => toggleAnalysis(message.id)}
                      onToggleSources={() => toggleSources(message.id)}
                    />
                  </div>

                  {/* Floating Inspection Panels (Right Column) */}
                  <div className="flex flex-col gap-5 lg:col-span-5 lg:pl-4">
                    <AnimatePresence>
                      {panelState.analysis && (
                        <motion.div
                          key="analysis"
                          initial={{ opacity: 0, x: 12, scale: 0.98 }}
                          animate={{ opacity: 1, x: 0, scale: 1 }}
                          exit={{ opacity: 0, x: 8, scale: 0.98 }}
                          transition={{ duration: 0.25 }}
                          className="relative"
                        >
                          <VerificationAnalysisCard
                            verification={message.verification}
                            score={message.verification?.score ?? undefined}
                            note={
                              message.verification?.note ??
                              (!message.verification?.performed
                                ? "Conversational response. No factual or empirical claims required verification."
                                : undefined)
                            }
                            onClose={() => toggleAnalysis(message.id)}
                          />
                        </motion.div>
                      )}

                      {panelState.sources && (
                        <motion.div
                          key="sources"
                          initial={{ opacity: 0, x: 12, scale: 0.98 }}
                          animate={{ opacity: 1, x: 0, scale: 1 }}
                          exit={{ opacity: 0, x: 8, scale: 0.98 }}
                          transition={{ duration: 0.25 }}
                        >
                          <SourcesCard
                            sources={message.sources}
                            onClose={() => toggleSources(message.id)}
                          />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              );
            })}
            <div ref={endRef} />
          </div>
        </div>
      </div>

      {/* Floating Bottom Chat Input matching Image 1 */}
      <div className="fixed inset-x-0 bottom-0 z-20 pointer-events-none pb-6 pt-4 bg-gradient-to-t from-[#FBFBFC] via-[#FBFBFC]/90 to-transparent">
        <div className="mx-auto max-w-2xl px-4 pointer-events-auto">
          <ChatInput
            value={input}
            onChange={onInput}
            onSend={onSend}
            onAttach={onAttach}
            onToggleWeb={onToggleWeb}
            webEnabled={webEnabled}
            busy={busy}
            isLanding={false}
          />
        </div>
      </div>
    </div>
  );
}
