from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from schemas.chat import VerificationStatus


def score_claims(results: List[Dict[str, Any]]) -> Tuple[Optional[float], Dict[str, int], Dict[str, Optional[int]]]:
    counts = {
        "supported": 0,
        "partial": 0,
        "unverified": 0,
        "contradicted": 0,
    }
    if not results:
        metrics = {
            "verified": None,
            "partiallyVerified": None,
            "unverified": None,
            "conflicting": None,
        }
        return None, counts, metrics

    for item in results:
        raw_status = str(item.get("status") or "").upper()
        if raw_status in {"SUPPORTED", "VERIFIED"}:
            counts["supported"] += 1
        elif raw_status in {"PARTIALLY_SUPPORTED", "PARTIAL", "PARTIALLY_VERIFIED"}:
            counts["partial"] += 1
        elif raw_status in {"CONTRADICTED", "CONFLICTING"}:
            counts["contradicted"] += 1
        else:
            counts["unverified"] += 1

    total = len(results)
    score = counts["supported"] / total if total > 0 else None

    # Calculate exact integer percentages from claim counts
    verified_pct = round((counts["supported"] / total) * 100)
    partial_pct = round((counts["partial"] / total) * 100)
    unverified_pct = round((counts["unverified"] / total) * 100)
    conflicting_pct = round((counts["contradicted"] / total) * 100)

    # Ensure percentages sum to 100% if total > 0
    diff = 100 - (verified_pct + partial_pct + unverified_pct + conflicting_pct)
    if diff != 0:
        # Adjust the largest category
        largest = max(
            [("verified", verified_pct), ("partial", partial_pct), ("unverified", unverified_pct), ("conflicting", conflicting_pct)],
            key=lambda x: x[1],
        )[0]
        if largest == "verified":
            verified_pct += diff
        elif largest == "partial":
            partial_pct += diff
        elif largest == "unverified":
            unverified_pct += diff
        else:
            conflicting_pct += diff

    metrics = {
        "verified": verified_pct,
        "partiallyVerified": partial_pct,
        "unverified": unverified_pct,
        "conflicting": conflicting_pct,
    }
    return score, counts, metrics


def overall_status(results: List[Dict[str, Any]], contradictions: Optional[Dict[str, Any]] = None) -> VerificationStatus:
    if not results:
        return VerificationStatus.UNVERIFIED

    has_conflict = bool((contradictions or {}).get("has_conflict"))
    statuses = {str(r.get("status") or "").upper() for r in results}

    if has_conflict or "CONTRADICTED" in statuses or "CONFLICTING" in statuses:
        return VerificationStatus.CONFLICTING

    # 100% verified is allowed ONLY when every relevant claim passed verification
    if statuses <= {"SUPPORTED", "VERIFIED"}:
        return VerificationStatus.VERIFIED

    if "SUPPORTED" in statuses or "VERIFIED" in statuses or "PARTIALLY_SUPPORTED" in statuses or "PARTIALLY_VERIFIED" in statuses:
        return VerificationStatus.PARTIALLY_VERIFIED

    return VerificationStatus.UNVERIFIED


def verification_note(status: VerificationStatus) -> Optional[str]:
    notes = {
        VerificationStatus.PARTIALLY_VERIFIED: "Verification note: Some information in this answer could not be independently confirmed from reliable sources.",
        VerificationStatus.UNVERIFIED: "Verification note: Information could not be independently verified from reliable sources.",
        VerificationStatus.CONFLICTING: "Verification note: Conflicting sources were found for this information.",
        VerificationStatus.VERIFICATION_INCOMPLETE: "Verification note: Independent verification could not be completed.",
        VerificationStatus.ERROR: "Verification note: Independent verification could not be completed.",
    }
    return notes.get(status)
