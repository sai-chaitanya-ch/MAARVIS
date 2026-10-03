import { useEffect, useState } from "react";
import { X, MessageSquare, Plus, Trash2, Clock, Loader2 } from "lucide-react";
import { fetchConversations, deleteConversation } from "../lib/api";

interface ConversationItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

interface GroupedConversations {
  today: ConversationItem[];
  yesterday: ConversationItem[];
  previous7Days: ConversationItem[];
  older: ConversationItem[];
}

interface HistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
}

function groupConversations(items: ConversationItem[]): GroupedConversations {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 24 * 60 * 60 * 1000;
  const startOf7Days = startOfToday - 7 * 24 * 60 * 60 * 1000;

  const grouped: GroupedConversations = {
    today: [],
    yesterday: [],
    previous7Days: [],
    older: [],
  };

  for (const item of items) {
    const timestamp = new Date(item.updated_at || item.created_at).getTime();
    if (timestamp >= startOfToday) {
      grouped.today.push(item);
    } else if (timestamp >= startOfYesterday) {
      grouped.yesterday.push(item);
    } else if (timestamp >= startOf7Days) {
      grouped.previous7Days.push(item);
    } else {
      grouped.older.push(item);
    }
  }

  return grouped;
}

function formatRelativeTime(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    if (diffMinutes < 1) return "Just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

export default function HistorySidebar({
  isOpen,
  onClose,
  activeConversationId,
  onSelectConversation,
  onNewChat,
}: HistorySidebarProps) {
  const [items, setItems] = useState<ConversationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadList = async () => {
    try {
      setLoading(true);
      const data = await fetchConversations();
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadList();
    }
  }, [isOpen]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      setDeletingId(id);
      await deleteConversation(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      if (activeConversationId === id) {
        onNewChat();
      }
    } catch {
      // ignore
    } finally {
      setDeletingId(null);
    }
  };

  if (!isOpen) return null;

  const grouped = groupConversations(items);

  const renderGroup = (title: string, list: ConversationItem[]) => {
    if (list.length === 0) return null;
    return (
      <div className="mb-4">
        <h4 className="px-3 text-[11px] font-semibold uppercase tracking-wider text-neutral-400 mb-1.5">
          {title}
        </h4>
        <div className="space-y-0.5">
          {list.map((item) => {
            const isActive = activeConversationId === item.id;
            return (
              <div
                key={item.id}
                onClick={() => {
                  onSelectConversation(item.id);
                  onClose();
                }}
                className={`group flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-xs font-medium cursor-pointer transition-all ${
                  isActive
                    ? "bg-neutral-900 text-white shadow-sm"
                    : "text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900"
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <MessageSquare
                    size={14}
                    className={`shrink-0 ${isActive ? "text-neutral-300" : "text-neutral-400"}`}
                  />
                  <span className="truncate">{item.title || "Untitled Chat"}</span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span
                    className={`text-[10px] ${
                      isActive ? "text-neutral-300" : "text-neutral-400"
                    }`}
                  >
                    {formatRelativeTime(item.updated_at || item.created_at)}
                  </span>
                  <button
                    type="button"
                    aria-label="Delete conversation"
                    disabled={deletingId === item.id}
                    onClick={(e) => handleDelete(e, item.id)}
                    className={`opacity-0 group-hover:opacity-100 p-1 rounded transition ${
                      isActive
                        ? "text-neutral-300 hover:bg-neutral-800 hover:text-rose-300"
                        : "text-neutral-400 hover:bg-neutral-200 hover:text-rose-600"
                    }`}
                  >
                    {deletingId === item.id ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Trash2 size={12} />
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex bg-black/20 backdrop-blur-[2px]">
      <div
        className="w-full max-w-sm h-full bg-white border-r border-[#E5E7EB] shadow-2xl flex flex-col animate-in slide-in-from-left duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] px-4 py-3.5">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-neutral-600" />
            <h3 className="text-sm font-semibold text-neutral-900">Chat History</h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close history"
            className="rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-800 transition"
          >
            <X size={16} />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3 border-b border-[#E5E7EB]">
          <button
            onClick={() => {
              onNewChat();
              onClose();
            }}
            className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-neutral-900 px-3 py-2 text-xs font-medium text-white hover:bg-neutral-800 transition shadow-sm"
          >
            <Plus size={14} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-3">
          {loading && items.length === 0 ? (
            <div className="flex justify-center py-10">
              <Loader2 size={20} className="animate-spin text-neutral-400" />
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-12 px-4">
              <MessageSquare size={24} className="mx-auto mb-2 text-neutral-300" />
              <p className="text-xs text-neutral-500">No conversations yet.</p>
              <p className="text-[11px] text-neutral-400 mt-1">
                Your past chats will appear here automatically.
              </p>
            </div>
          ) : (
            <div>
              {renderGroup("Today", grouped.today)}
              {renderGroup("Yesterday", grouped.yesterday)}
              {renderGroup("Previous 7 Days", grouped.previous7Days)}
              {renderGroup("Older", grouped.older)}
            </div>
          )}
        </div>
      </div>

      <div className="flex-1" onClick={onClose} />
    </div>
  );
}
