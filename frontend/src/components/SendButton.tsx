import { ArrowUp } from "lucide-react";

export default function SendButton({ disabled }: { disabled: boolean }) {
  return (
    <button
      type="submit"
      disabled={disabled}
      aria-label="Send message"
      className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-accent text-white disabled:bg-neutral-200"
    >
      <ArrowUp size={16} />
    </button>
  );
}
