import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { fetchConversations, fetchConversation, ChatMessage } from "../lib/api";

export default function HistoryMenu({
  onLoad,
}: {
  onLoad: (id: string, messages: ChatMessage[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<{ id: string; title: string }[]>([]);

  useEffect(() => {
    if (!open) return;
    fetchConversations()
      .then(setItems)
      .catch(() => setItems([]));
  }, [open]);

  return (
    <div className="fixed right-4 top-4 z-20">
      <button
        type="button"
        aria-label="Conversation history"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-9 w-9 items-center justify-center rounded-full text-mute hover:bg-neutral-50"
      >
        <History size={16} />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-64 rounded-xl border border-line bg-white p-2 shadow-sm">
          {items.length === 0 && <p className="px-2 py-3 text-xs text-mute">No conversations yet.</p>}
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              className="block w-full truncate rounded-lg px-2 py-2 text-left text-sm hover:bg-neutral-50"
              onClick={async () => {
                const data = await fetchConversation(item.id);
                const msgs = (data.messages || []).map((m: Record<string, unknown>) => ({
                  id: m.id,
                  role: m.role,
                  content: m.content,
                  verification: m.verification,
                  sources: m.sources,
                  claims: m.claims,
                  events: m.events,
                }));
                onLoad(item.id, msgs);
                setOpen(false);
              }}
            >
              {item.title}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
