export const ACTIVITY_LABELS: Record<string, string> = {
  routing: "Understanding your request…",
  web_search: "Searching the web…",
  web_extract: "Analyzing sources…",
  retrieval: "Reading your document…",
  reranking: "Ranking passages…",
  calculation: "Calculating…",
  code_execution: "Running code…",
  generating: "Preparing answer…",
  claim_extraction: "Checking claims…",
  verification: "Verifying evidence…",
  contradiction_check: "Comparing sources…",
  critic: "Reviewing evidence…",
  correction: "Revising the answer…",
  finalization: "Preparing answer…",
};

export function labelFor(event: string) {
  return ACTIVITY_LABELS[event] || null;
}
