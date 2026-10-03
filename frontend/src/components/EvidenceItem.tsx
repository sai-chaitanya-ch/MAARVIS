import { Source } from "../lib/api";

export default function EvidenceItem({ source }: { source: Source }) {
  return (
    <div className="text-[12px]">
      <p className="text-ink">{source.title}</p>
      {source.evidence && <p className="mt-1 line-clamp-3 text-mute">{source.evidence}</p>}
    </div>
  );
}
