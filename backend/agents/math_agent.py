from __future__ import annotations

from typing import Any, Dict

from tools.calculator import MathResult, parse_math_query


def run_math(question: str) -> Dict[str, Any]:
    result: MathResult = parse_math_query(question)
    verified = result.comparison is not False and not result.incomplete and not result.error
    payload: Dict[str, Any] = {
        "draft_answer": result.display,
        "calculation_result": {
            "expression": result.expression,
            "value": result.value,
            "comparison": result.comparison,
            "incomplete": result.incomplete,
            "error": result.error,
        },
        "incomplete": result.incomplete,
    }
    if result.comparison is not None and not result.incomplete:
        from verification.confidence import build_verification_payload
        claim_status = "SUPPORTED" if verified else "CONTRADICTED"
        claim_obj = {
            "claim_id": "c1",
            "claim_text": result.expression,
            "status": claim_status,
            "confidence": 1.0,
            "evidence_ids": ["calculator"],
            "reason": "Deterministic arithmetic evaluation.",
            "importance": "high",
        }
        payload["tool_verification"] = build_verification_payload(
            performed=True,
            results=[claim_obj],
            level=1,
            independent_completed=True,
            methods=["deterministic_calculator"],
        )
        if not verified:
            payload["tool_verification"]["note"] = "Verification note: The stated equation is not mathematically correct."
        else:
            payload["tool_verification"]["note"] = "Deterministic arithmetic verified by calculator."
        payload["claims"] = [
            {
                "claim_id": "c1",
                "claim_text": result.expression,
                "status": "SUPPORTED" if verified else "CONTRADICTED",
                "confidence": 1.0,
                "evidence_ids": ["calculator"],
                "reason": "Deterministic arithmetic evaluation.",
                "importance": "high",
            }
        ]
        payload["sources"] = [
            {
                "id": "calculator",
                "title": "Deterministic calculator",
                "url": None,
                "domain": None,
                "source_type": "calculation",
                "evidence": f"{result.expression} → {result.value} (equal={result.comparison})",
            }
        ]
    return payload
