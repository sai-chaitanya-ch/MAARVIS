import { Source } from "../lib/api";
import SourceItem from "./SourceItem";

export default function SourceList({ sources }: { sources: Source[] }) {
  const visible = sources.filter((s) => s.url || s.source_type === "document");
  if (!visible.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {visible.slice(0, 6).map((source) => (
        <SourceItem key={source.id} source={source} />
      ))}
    </div>
  );
}
