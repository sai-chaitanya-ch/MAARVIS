import { useCallback, useRef, useState } from "react";
import {
  streamChat,
  uploadDocument,
  fetchConversation,
  type ChatMessage,
  type AgentEvent,
  type StreamEvent,
} from "../lib/api";
import { labelFor } from "../lib/activity";
import type { MarvisMode } from "../components/MarvisModeSelector";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [activity, setActivity] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [webEnabled, setWebEnabled] = useState<boolean | null>(null);
  const [mode, setMode] = useState<MarvisMode>("AUTO");
  const abortRef = useRef<AbortController | null>(null);

  const isEmpty = messages.length === 0 && !busy;

  const send = useCallback(
    async (text?: string) => {
      const message = (text ?? input).trim();
      if (!message || busy) return;
      setInput("");
      setError(null);
      setBusy(true);
      setActivity("Preparing answer\u2026");

      // Consume attachments for this message so subsequent requests don't leak stale RAG
      const currentDocIds = [...documentIds];
      setDocumentIds([]);
      setAttachedFiles([]);

      const userMsg: ChatMessage = { id: `u_${Date.now()}`, role: "user", content: message };
      setMessages((prev) => [...prev, userMsg]);
      const assistantId = `a_${Date.now()}`;
      setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: "", events: [] }]);

      const events: AgentEvent[] = [];
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        await streamChat(
          {
            message,
            conversation_id: conversationId,
            document_ids: currentDocIds,
            web_enabled: webEnabled,
            mode,
          },
          (event: StreamEvent) => {
            if (event.type === "activity") {
              const name = String(event.event || "");
              const status = String(event.status || "");
              events.push({ event: name, status, detail: event.detail as string | undefined });
              const label = labelFor(name);
              if (label && status === "started") setActivity(label);
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? { ...m, events: [...events] } : m))
              );
            } else if (event.type === "token") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: m.content + String(event.content || "") } : m
                )
              );
            } else if (event.type === "complete") {
              if (event.conversation_id) setConversationId(String(event.conversation_id));
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: String(event.answer || m.content),
                        verification: event.verification as ChatMessage["verification"],
                        sources: (event.sources as ChatMessage["sources"]) || [],
                        claims: (event.claims as ChatMessage["claims"]) || [],
                        events: (event.events as AgentEvent[]) || events,
                        routing: event.routing as ChatMessage["routing"],
                        execution_id:
                          (event.execution_id as string) ||
                          (event.verification as any)?.execution_id,
                        execution_trace:
                          (event.execution_trace as any) ||
                          (event.verification as any)?.execution_trace,
                        capabilities:
                          (event.capabilities as any) ||
                          (event.execution_trace as any)?.capabilities,
                        recommendations:
                          (event.recommendations as any) ||
                          (event.execution_trace as any)?.recommendations,
                      }
                    : m
                )
              );
              setActivity(null);
            } else if (event.type === "error") {
              setError(String(event.message || "Something went wrong"));
            }
          },
          controller.signal
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      } finally {
        setBusy(false);
        setActivity(null);
      }
    },
    [busy, conversationId, documentIds, input, webEnabled, mode]
  );

  const [attachedFiles, setAttachedFiles] = useState<{ id: string; name: string }[]>([]);

  const attach = useCallback(async (file: File) => {
    setError(null);
    const result = await uploadDocument(file);
    setDocumentIds((prev) => [...prev, result.document_id]);
    setAttachedFiles((prev) => [...prev, { id: result.document_id, name: file.name }]);
    return result;
  }, []);

  const removeAttachment = useCallback((index: number) => {
    setAttachedFiles((prev) => {
      const target = prev[index];
      if (target) {
        setDocumentIds((dPrev) => dPrev.filter((id) => id !== target.id));
      }
      return prev.filter((_, i) => i !== index);
    });
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setConversationId(null);
    setInput("");
    setActivity(null);
    setError(null);
    setDocumentIds([]);
    setAttachedFiles([]);
  }, []);

  const newChat = useCallback(() => {
    reset();
  }, [reset]);

  const loadConversation = useCallback(async (id: string) => {
    try {
      abortRef.current?.abort();
      setBusy(true);
      setError(null);
      setActivity("Loading conversation…");
      const data = await fetchConversation(id);
      setConversationId(id);
      const loaded: ChatMessage[] = (data.messages || []).map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        verification: m.verification_json
          ? (typeof m.verification_json === "string" ? JSON.parse(m.verification_json) : m.verification_json)
          : undefined,
        sources: m.sources_json
          ? (typeof m.sources_json === "string" ? JSON.parse(m.sources_json) : m.sources_json)
          : [],
        events: m.events_json
          ? (typeof m.events_json === "string" ? JSON.parse(m.events_json) : m.events_json)
          : [],
        claims: m.claims_json
          ? (typeof m.claims_json === "string" ? JSON.parse(m.claims_json) : m.claims_json)
          : [],
        routing: m.routing_json
          ? (typeof m.routing_json === "string" ? JSON.parse(m.routing_json) : m.routing_json)
          : undefined,
        execution_id: m.execution_id,
        execution_trace: m.execution_trace_json
          ? (typeof m.execution_trace_json === "string" ? JSON.parse(m.execution_trace_json) : m.execution_trace_json)
          : undefined,
      }));
      setMessages(loaded);
    } catch (e: any) {
      setError(e.message || "Failed to load conversation");
    } finally {
      setBusy(false);
      setActivity(null);
    }
  }, []);

  return {
    messages,
    conversationId,
    input,
    setInput,
    busy,
    activity,
    error,
    isEmpty,
    send,
    attach,
    removeAttachment,
    reset,
    newChat,
    loadConversation,
    documentIds,
    attachedFiles,
    webEnabled,
    setWebEnabled,
    setMessages,
    setConversationId,
    mode,
    setMode,
  };
}
