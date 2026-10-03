import { motion } from "framer-motion";
import ChatInput from "./ChatInput";

export default function LandingScreen({
  input,
  onInput,
  onSend,
  onAttach,
  onToggleWeb,
  webEnabled,
  busy,
  onSelectPrompt,
}: {
  input: string;
  onInput: (v: string) => void;
  onSend: () => void;
  onAttach: (file: File) => void;
  onToggleWeb: () => void;
  webEnabled: boolean | null;
  busy: boolean;
  onSelectPrompt?: (prompt: string) => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl flex-col items-center justify-center px-4 pb-16 pt-8 text-center"
    >
      {/* Hero Typography Matching Image 2 */}
      <motion.h1
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="text-6xl font-bold tracking-tight text-neutral-900 sm:text-7xl select-none"
      >
        MAARVIS
      </motion.h1>

      {/* Subtitle Tagline */}
      <motion.p
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="mt-2 text-xl font-normal tracking-wide text-slate-400 sm:text-2xl"
      >
        Verify. Reason. Trust.
      </motion.p>

      {/* Description */}
      <motion.p
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.16 }}
        className="mx-auto mt-6 max-w-xl text-[14.5px] leading-relaxed text-neutral-500 sm:text-[15px]"
      >
        MAARVIS is your AI-powered verification and reasoning platform — research the web,
        analyze documents, solve problems, and get verified answers.
      </motion.p>

      {/* Floating Pill Input Bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.22 }}
        className="mt-10 w-full max-w-2xl text-left"
      >
        <ChatInput
          value={input}
          onChange={onInput}
          onSend={onSend}
          onAttach={onAttach}
          onToggleWeb={onToggleWeb}
          webEnabled={webEnabled}
          busy={busy}
          autoFocus
          isLanding
        />
      </motion.div>
    </motion.div>
  );
}
