import { ClaimResult } from "../lib/api";
import ClaimItem from "./ClaimItem";

export default function ClaimList({ claims }: { claims: ClaimResult[] }) {
  if (!claims.length) return null;
  return (
    <ul className="space-y-1.5">
      {claims.map((c) => (
        <ClaimItem key={c.claim_id} claim={c} />
      ))}
    </ul>
  );
}
