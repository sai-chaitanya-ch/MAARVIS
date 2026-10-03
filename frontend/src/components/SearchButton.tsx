import { Globe } from "lucide-react";

export default function SearchButton({ active, onClick }: { active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label="Toggle web search"
      className={`inline-flex h-8 w-8 items-center justify-center rounded-lg hover:bg-neutral-50 ${
        active ? "text-accent" : "text-mute"
      }`}
    >
      <Globe size={16} />
    </button>
  );
}
