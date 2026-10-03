import { motion } from "framer-motion";
import { AgentEvent } from "../lib/api";
import { labelFor } from "../lib/activity";

export default function ActivityIndicator({ events }: { events: AgentEvent[] }) {
  // Find the most recent "started" event to show what's happening right now
  const started = [...events].reverse().find((e) => e.status === "started");
  const label = started ? labelFor(started.event) : "Preparing answer…";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex items-center gap-2.5"
      aria-live="polite"
      aria-atomic="true"
    >
      {/* Pulsing dots */}
      <div className="flex items-center gap-[3px]" aria-hidden>
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="inline-block h-1.5 w-1.5 rounded-full bg-neutral-300"
            animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
            transition={{
              duration: 1.1,
              delay: i * 0.18,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
      <span className="text-[13.5px] text-neutral-400">{label}</span>
    </motion.div>
  );
}
