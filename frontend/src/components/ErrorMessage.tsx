import { motion } from "framer-motion";
import { AlertCircle } from "lucide-react";

export default function ErrorMessage({ message }: { message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto mb-4 max-w-2xl px-4"
    >
      <div className="flex items-start gap-2.5 rounded-xl border border-red-100 bg-red-50 px-4 py-3">
        <AlertCircle size={15} className="mt-0.5 flex-shrink-0 text-red-400" />
        <p className="text-[13px] leading-5 text-red-600">{message}</p>
      </div>
    </motion.div>
  );
}
