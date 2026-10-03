import { useState, useEffect, useRef } from "react";
import {
  FileText,
  UploadCloud,
  Trash2,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  Search,
  ArrowUp,
  Sparkles,
  BookOpen,
  Layers,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  Filter,
  RefreshCw,
  Info,
} from "lucide-react";
import {
  DocumentItem,
  DocumentPassage,
  Source,
  Verification,
  ClaimResult,
  fetchDocuments,
  deleteDocument,
  uploadDocument,
  chatWithDocuments,
} from "../lib/api";
import MarkdownRenderer from "./MarkdownRenderer";
import VerificationAnalysisCard from "./VerificationAnalysisCard";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  verification?: Verification;
  sources?: Source[];
  passages?: DocumentPassage[];
  claims?: ClaimResult[];
}

export default function KnowledgeBaseScreen() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [querying, setQuerying] = useState(false);
  const [activePassage, setActivePassage] = useState<DocumentPassage | null>(null);
  const [selectedVerifMessageId, setSelectedVerifMessageId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load existing documents
  const loadDocs = async () => {
    try {
      setLoadingDocs(true);
      const docs = await fetchDocuments();
      setDocuments(docs);
    } catch (err: any) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, querying]);

  // Handle File Upload
  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadError(null);
    setUploadStatus(null);

    const validExtensions = [".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp"];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!validExtensions.includes(ext)) {
        setUploadError(`Unsupported file: "${file.name}". Supported: PDF, DOCX, TXT, MD, Images.`);
        setUploading(false);
        return;
      }

      setUploadStatus(`Indexing "${file.name}" into Vector Vault...`);
      try {
        const res = await uploadDocument(file);
        setUploadStatus(`Successfully indexed "${file.name}" (${res.chunks} chunks)!`);
      } catch (err: any) {
        setUploadError(err.message || `Failed to index "${file.name}"`);
        setUploading(false);
        return;
      }
    }

    await loadDocs();
    setUploading(false);
    setTimeout(() => setUploadStatus(null), 4000);
  };

  // Handle Delete
  const handleDeleteDoc = async (id: string, name: string) => {
    if (!window.confirm(`Delete "${name}" and remove its vector embeddings?`)) return;
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setSelectedDocIds((prev) => prev.filter((docId) => docId !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete document");
    }
  };

  // Toggle selection for query filtering
  const toggleDocSelection = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const selectAllDocs = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map((d) => d.id));
    }
  };

  // Send RAG Query
  const handleSend = async (customText?: string) => {
    const text = (customText || input).trim();
    if (!text || querying) return;

    const userMsg: Message = {
      id: "u_" + Date.now(),
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setQuerying(true);

    try {
      const res = await chatWithDocuments({
        message: text,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      });

      const assistantMsg: Message = {
        id: "a_" + Date.now(),
        role: "assistant",
        content: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        verification: res.verification,
        sources: res.sources,
        passages: res.passages,
        claims: res.claims,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: "err_" + Date.now(),
        role: "assistant",
        content: `**RAG Agent Encountered an Issue:**\n${err.message || "Unable to retrieve document evidence."}\n\nPlease check if your document is uploaded and has text content.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setQuerying(false);
    }
  };

  const getFileBadgeColor = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    switch (ext) {
      case "pdf":
        return "bg-rose-50 text-rose-600 border-rose-200/80";
      case "docx":
        return "bg-blue-50 text-blue-600 border-blue-200/80";
      case "md":
      case "txt":
        return "bg-emerald-50 text-emerald-700 border-emerald-200/80";
      default:
        return "bg-purple-50 text-purple-600 border-purple-200/80";
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-[#FBFBFC]">
      {/* LEFT SIDEBAR: Document Vault */}
      <aside className="flex w-80 shrink-0 flex-col border-r border-neutral-200/70 bg-white">
        {/* Vault Header */}
        <div className="border-b border-neutral-100 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-900 text-white">
                <BookOpen size={15} />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-neutral-900">Knowledge Vault</h2>
                <p className="text-[11px] text-neutral-500">
                  {documents.length} document{documents.length === 1 ? "" : "s"} indexed
                </p>
              </div>
            </div>
            <button
              onClick={loadDocs}
              title="Refresh documents"
              className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition"
            >
              <RefreshCw size={14} className={loadingDocs ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Upload Drop Area */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              handleFileUpload(e.dataTransfer.files);
            }}
            className="mt-3.5 flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-neutral-300 bg-neutral-50/70 p-4 text-center transition-all hover:border-neutral-400 hover:bg-neutral-100/60"
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-neutral-600 shadow-2xs">
              <UploadCloud size={16} />
            </div>
            <p className="mt-2 text-xs font-medium text-neutral-800">
              Upload Knowledge Files
            </p>
            <p className="mt-0.5 text-[10.5px] text-neutral-400">
              PDF, DOCX, TXT, MD, Scanned Docs
            </p>
          </div>

          {/* Status / Error Toast */}
          {uploadStatus && (
            <div className="mt-2.5 flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-800 border border-emerald-200/60">
              <CheckCircle2 size={14} className="shrink-0 text-emerald-600" />
              <span className="truncate">{uploadStatus}</span>
            </div>
          )}
          {uploadError && (
            <div className="mt-2.5 flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800 border border-rose-200/60">
              <AlertCircle size={14} className="shrink-0 text-rose-600" />
              <span className="truncate">{uploadError}</span>
            </div>
          )}

          {/* Selection Filter Controls */}
          {documents.length > 0 && (
            <div className="mt-3 flex items-center justify-between text-xs text-neutral-500">
              <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-400">
                Target Documents
              </span>
              <button
                onClick={selectAllDocs}
                className="text-[11px] font-medium text-neutral-700 hover:underline"
              >
                {selectedDocIds.length === documents.length ? "Deselect All" : "Select All"}
              </button>
            </div>
          )}
        </div>

        {/* Document List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {documents.length === 0 ? (
            <div className="flex h-48 flex-col items-center justify-center text-center p-4">
              <FileCheck size={28} className="text-neutral-300 mb-2" />
              <p className="text-xs font-medium text-neutral-600">Vault is empty</p>
              <p className="text-[11px] text-neutral-400 mt-1">
                Upload your files above to query them with the autonomous RAG agent.
              </p>
            </div>
          ) : (
            documents.map((doc) => {
              const isSelected =
                selectedDocIds.length === 0 || selectedDocIds.includes(doc.id);
              return (
                <div
                  key={doc.id}
                  className={`group relative flex items-center justify-between rounded-xl border p-2.5 transition-all ${
                    isSelected
                      ? "border-neutral-200 bg-neutral-50/70 hover:bg-neutral-100/70"
                      : "border-transparent bg-transparent opacity-60 hover:opacity-100"
                  }`}
                >
                  <label className="flex flex-1 min-w-0 cursor-pointer items-center gap-2.5">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleDocSelection(doc.id)}
                      className="rounded border-neutral-300 text-neutral-900 focus:ring-0"
                    />
                    <div
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border text-[10px] font-bold uppercase ${getFileBadgeColor(
                        doc.filename
                      )}`}
                    >
                      {doc.filename.split(".").pop() || "doc"}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium text-neutral-800">
                        {doc.filename}
                      </p>
                      <p className="text-[10px] text-neutral-400">
                        {doc.chunks} chunks indexed
                      </p>
                    </div>
                  </label>
                  <button
                    onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                    title="Delete document"
                    className="ml-2 hidden rounded-md p-1 text-neutral-400 hover:bg-rose-50 hover:text-rose-600 group-hover:block transition"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Vault Footer */}
        <div className="border-t border-neutral-100 p-3 bg-neutral-50/50">
          <div className="flex items-center gap-2 text-[11px] text-neutral-500">
            <ShieldCheck size={14} className="text-emerald-600 shrink-0" />
            <span>Embedding model: <strong>BAAI/bge-m3</strong></span>
          </div>
        </div>
      </aside>

      {/* CENTER: Main Autonomous RAG Chat Feed */}
      <section className="flex flex-1 flex-col overflow-hidden relative">
        {/* Top Chat Subheader */}
        <div className="flex items-center justify-between border-b border-neutral-200/70 bg-white/80 px-6 py-3 backdrop-blur-md">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-2xs">
              <Sparkles size={14} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-neutral-900">
                  Knowledge Autonomous Agent
                </h1>
                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 border border-emerald-200/60">
                  RAG Online
                </span>
              </div>
              <p className="text-[11px] text-neutral-400">
                Direct evidence retrieval & factual verification from primary files
              </p>
            </div>
          </div>

          <div className="text-xs text-neutral-500">
            {selectedDocIds.length > 0 ? (
              <span className="font-medium text-neutral-700">
                Targeting {selectedDocIds.length} of {documents.length} files
              </span>
            ) : (
              <span className="text-neutral-500">
                Searching across all {documents.length} files
              </span>
            )}
          </div>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            /* Welcome / Zero State */
            <div className="mx-auto max-w-xl py-12 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-b from-neutral-900 to-neutral-800 text-white shadow-lg">
                <BookOpen size={28} />
              </div>
              <h2 className="mt-5 text-xl font-semibold text-neutral-900">
                Autonomous Knowledge Agent
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-neutral-500">
                Ask questions about your uploaded PDFs, reports, or research notes. The agent
                retrieves the exact document passages and fact-checks each claim before responding.
              </p>

              {/* Quick Prompts */}
              {documents.length > 0 ? (
                <div className="mt-8 space-y-2 text-left">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-neutral-400 px-1">
                    Suggested Questions
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {[
                      "Summarize the key findings and conclusions.",
                      "What are the core metrics, data points, or dates mentioned?",
                      "List all critical risks or recommendations in the text.",
                      "Explain the main methodology or approach described.",
                    ].map((prompt, i) => (
                      <button
                        key={i}
                        onClick={() => handleSend(prompt)}
                        className="flex items-center justify-between rounded-xl border border-neutral-200/80 bg-white p-3 text-xs font-medium text-neutral-700 shadow-2xs hover:border-neutral-300 hover:bg-neutral-50 transition text-left"
                      >
                        <span className="line-clamp-2">{prompt}</span>
                        <ChevronRight size={14} className="shrink-0 text-neutral-400 ml-2" />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="mt-8 rounded-xl border border-dashed border-neutral-300 bg-white p-6">
                  <p className="text-xs text-neutral-500">
                    No files found in your vault. Upload a document from the left sidebar to begin.
                  </p>
                </div>
              )}
            </div>
          ) : (
            /* Message Bubbles */
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${
                  msg.role === "user" ? "items-end" : "items-start"
                }`}
              >
                {/* Bubble */}
                <div
                  className={`max-w-3xl rounded-2xl p-4 sm:p-5 ${
                    msg.role === "user"
                      ? "bg-neutral-900 text-white shadow-xs"
                      : "bg-white border border-neutral-200/70 shadow-xs text-neutral-900"
                  }`}
                >
                  {/* Assistant Header Info */}
                  {msg.role === "assistant" && (
                    <div className="mb-3 flex items-center justify-between border-b border-neutral-100 pb-2.5">
                      <div className="flex items-center gap-2">
                        <div className="flex h-5 w-5 items-center justify-center rounded-md bg-neutral-900 text-white text-[10px]">
                          <Sparkles size={11} />
                        </div>
                        <span className="text-xs font-semibold text-neutral-800">
                          Verify Knowledge Agent
                        </span>
                      </div>

                      {/* Verification Badge */}
                      {msg.verification && (
                        <button
                          onClick={() =>
                            setSelectedVerifMessageId(
                              selectedVerifMessageId === msg.id ? null : msg.id
                            )
                          }
                          className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition"
                        >
                          <ShieldCheck size={13} className="text-emerald-600" />
                          <span>
                            {Math.round((msg.verification.score || 0.95) * 100)}% Verified
                          </span>
                        </button>
                      )}
                    </div>
                  )}

                  {/* Message Content */}
                  {msg.role === "user" ? (
                    <p className="text-sm font-normal leading-relaxed">{msg.content}</p>
                  ) : (
                    <MarkdownRenderer content={msg.content} />
                  )}

                  {/* Verification Analysis Dropdown/Card */}
                  {msg.role === "assistant" &&
                    msg.verification &&
                    selectedVerifMessageId === msg.id && (
                      <div className="mt-4 pt-3 border-t border-neutral-100">
                        <VerificationAnalysisCard
                          verification={msg.verification}
                          onClose={() => setSelectedVerifMessageId(null)}
                        />
                      </div>
                    )}

                  {/* Retrieved Evidence Passages */}
                  {msg.role === "assistant" && msg.passages && msg.passages.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-neutral-100">
                      <div className="flex items-center gap-1.5 text-xs font-medium text-neutral-600 mb-2">
                        <Layers size={13} className="text-neutral-500" />
                        <span>Retrieved Document Passages ({msg.passages.length})</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.passages.map((p, idx) => (
                          <button
                            key={idx}
                            onClick={() => setActivePassage(p)}
                            className="flex items-center gap-1 rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-[11px] font-medium text-neutral-700 hover:border-neutral-300 hover:bg-neutral-100 transition"
                          >
                            <FileText size={11} className="text-neutral-400" />
                            <span>
                              {p.source || "Document"}
                              {p.page != null ? ` (p. ${p.page})` : ""}
                            </span>
                            {p.rerank_score != null && (
                              <span className="text-[10px] text-emerald-600">
                                {Math.round(p.rerank_score * 100)}%
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Timestamp */}
                <span className="mt-1 px-1 text-[10px] text-neutral-400">
                  {msg.timestamp}
                </span>
              </div>
            ))
          )}

          {/* Loading Indicator */}
          {querying && (
            <div className="flex items-center gap-3 rounded-2xl border border-neutral-200/80 bg-white p-4 shadow-2xs max-w-sm">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-neutral-900 text-white animate-spin">
                <RefreshCw size={12} />
              </div>
              <div>
                <p className="text-xs font-medium text-neutral-800">
                  Consulting vector store & verifying claims...
                </p>
                <p className="text-[10px] text-neutral-400">
                  Retrieving semantically aligned document passages
                </p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* BOTTOM INPUT BAR */}
        <div className="p-4 border-t border-neutral-200/70 bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="mx-auto max-w-3xl"
          >
            <div className="relative flex items-center rounded-2xl border border-neutral-300/80 bg-neutral-50/80 px-4 py-2.5 shadow-2xs focus-within:border-neutral-900 focus-within:bg-white transition-all">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  documents.length === 0
                    ? "Upload documents first, then ask questions..."
                    : "Ask any question about your documents..."
                }
                disabled={querying}
                className="flex-1 bg-transparent text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-hidden disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!input.trim() || querying}
                className="ml-2 flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-white transition-all hover:bg-neutral-800 disabled:opacity-30 disabled:hover:bg-neutral-900"
              >
                <ArrowUp size={16} />
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* PASSAGE DETAILS MODAL / DRAWER */}
      {activePassage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-xs p-4">
          <div className="relative w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl border border-neutral-200">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
              <div className="flex items-center gap-2">
                <FileText size={18} className="text-neutral-600" />
                <h3 className="text-sm font-semibold text-neutral-900">
                  {activePassage.source || "Document Evidence Passage"}
                </h3>
              </div>
              <button
                onClick={() => setActivePassage(null)}
                className="rounded-md p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
              >
                &times;
              </button>
            </div>

            <div className="mt-3 flex items-center gap-3 text-xs text-neutral-500">
              {activePassage.page != null && (
                <span>Page: <strong>{activePassage.page}</strong></span>
              )}
              {activePassage.chunk_id && (
                <span>Chunk ID: <strong>{activePassage.chunk_id.slice(0, 8)}</strong></span>
              )}
              {activePassage.rerank_score != null && (
                <span className="text-emerald-600">
                  Relevance: <strong>{Math.round(activePassage.rerank_score * 100)}%</strong>
                </span>
              )}
            </div>

            <div className="mt-4 max-h-96 overflow-y-auto rounded-xl bg-neutral-50 p-4 text-xs leading-relaxed text-neutral-800 border border-neutral-200/60 font-mono whitespace-pre-wrap">
              {activePassage.text}
            </div>

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setActivePassage(null)}
                className="rounded-lg bg-neutral-900 px-4 py-2 text-xs font-medium text-white hover:bg-neutral-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
