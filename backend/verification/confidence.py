from __future__ import annotations

from typing import Any, Dict, List, Optional

from verification.scoring import overall_status, score_claims, verification_note
from schemas.chat import VerificationStatus


def build_verification_payload(
    performed: bool,
    results: Optional[List[Dict[str, Any]]] = None,
    contradictions: Optional[Dict[str, Any]] = None,
    level: Optional[int] = None,
    error: Optional[str] = None,
    independent_completed: bool = True,
    iterations: int = 1,
    methods: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if not performed:
        return {
            "performed": False,
            "independentVerificationCompleted": False,
            "independent_verification_completed": False,
            "status": VerificationStatus.UNVERIFIED.value,
            "metrics": {
                "verified": None,
                "partiallyVerified": None,
                "unverified": None,
                "conflicting": None,
            },
        }

    results = results or []
    total = len(results)

    # If verification failed or was incomplete:
    if error or not independent_completed:
        status = VerificationStatus.VERIFICATION_INCOMPLETE
        return {
            "performed": True,
            "independentVerificationCompleted": False,
            "independent_verification_completed": False,
            "status": status.value,
            "score": None,
            "totalClaims": total,
            "total_claims": total,
            "verifiedClaims": 0,
            "verified_claims": 0,
            "partiallyVerifiedClaims": 0,
            "partially_verified_claims": 0,
            "unverifiedClaims": total,
            "unverified_claims": total,
            "conflictingClaims": 0,
            "conflicting_claims": 0,
            "metrics": {
                "verified": None,
                "partiallyVerified": None,
                "unverified": None,
                "conflicting": None,
            },
            "claims": results,
            "evidence": [],
            "verificationMethods": methods or ["independent_verification"],
            "verification_methods": methods or ["independent_verification"],
            "iterations": iterations,
            "note": "Independent verification could not be completed.",
            "level": level,
            "error": error,
        }

    score, counts, metrics = score_claims(results)
    status = overall_status(results, contradictions)

    # 100% verified is allowed ONLY when:
    # independentVerificationCompleted === true AND all claims checked AND all passed verification AND no conflicting claims
    if counts["contradicted"] > 0:
        status = VerificationStatus.CONFLICTING
    elif total > 0 and counts["supported"] == total:
        status = VerificationStatus.VERIFIED
    elif counts["supported"] > 0 or counts["partial"] > 0:
        status = VerificationStatus.PARTIALLY_VERIFIED
    elif total > 0:
        status = VerificationStatus.UNVERIFIED
    else:
        status = VerificationStatus.UNVERIFIED

    return {
        "performed": True,
        "independentVerificationCompleted": True,
        "independent_verification_completed": True,
        "status": status.value,
        "score": score,
        "totalClaims": total,
        "total_claims": total,
        "verifiedClaims": counts["supported"],
        "verified_claims": counts["supported"],
        "partiallyVerifiedClaims": counts["partial"],
        "partially_verified_claims": counts["partial"],
        "unverifiedClaims": counts["unverified"],
        "unverified_claims": counts["unverified"],
        "conflictingClaims": counts["contradicted"],
        "conflicting_claims": counts["contradicted"],
        "claims_checked": total,
        "supported": counts["supported"],
        "partial": counts["partial"],
        "unverified": counts["unverified"],
        "contradicted": counts["contradicted"],
        "metrics": metrics,
        "claims": results,
        "evidence": [],
        "verificationMethods": methods or ["independent_verification"],
        "verification_methods": methods or ["independent_verification"],
        "iterations": iterations,
        "note": verification_note(status) if status != VerificationStatus.VERIFIED else None,
        "level": level,
    }

