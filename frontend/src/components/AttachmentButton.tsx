import { Paperclip } from "lucide-react";

export default function AttachmentButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Attach a document"
      className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-mute hover:bg-neutral-50"
    >
      <Paperclip size={16} />
    </button>
  );
}
