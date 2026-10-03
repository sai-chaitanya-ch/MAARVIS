import { Mic } from "lucide-react";

export default function VoiceButton() {
  return (
    <button
      type="button"
      aria-label="Voice input is not enabled yet"
      title="Voice input requires Whisper configuration in a later release"
      className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-mute hover:bg-neutral-50"
    >
      <Mic size={16} />
    </button>
  );
}
