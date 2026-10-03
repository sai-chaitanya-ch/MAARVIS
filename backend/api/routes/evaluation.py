from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from evaluation.dataset import get_all_test_cases, get_test_case_by_id
from evaluation.benchmarks import calculate_system_benchmarks
from evaluation.engine import EvaluationEngine

router = APIRouter()


class RunEvaluationRequest(BaseModel):
    case_id: Optional[str] = None
    query: Optional[str] = None


@router.get("/cases")
async def list_cases():
    """Returns all predefined evaluation cases for Judge Demonstration Mode."""
    cases = get_all_test_cases()
    return {
        "total": len(cases),
        "cases": [
            {
                "id": c["id"],
                "category": c["category"],
                "title": c["title"],
                "input": c["input"],
                "expected_decision": c.get("expected_decision"),
                "expected_verification": c.get("expected_verification"),
            }
            for c in cases
        ],
    }


@router.get("/benchmarks")
async def get_benchmarks():
    """Returns programmatically computed system benchmarks."""
    return calculate_system_benchmarks()


@router.get("/latest")
async def get_latest_run():
    """Returns the most recent verification run."""
    run = EvaluationEngine.get_latest()
    if not run:
        raise HTTPException(status_code=404, detail="No evaluation run found")
    return run


@router.post("/run")
async def run_evaluation(body: RunEvaluationRequest):
    """
    Executes an evaluation test case or custom verification run with complete multi-agent
    orchestration trace, audit log, claim verification, and metrics.
    """
    case_id = body.case_id
    if case_id:
        case = get_test_case_by_id(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case ID '{case_id}' not found")
        run_data = EvaluationEngine.build_case_run(case)
        EvaluationEngine.set_latest(run_data)
        return run_data

    query = (body.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Either case_id or query must be provided")

    # If it's a custom query, check if it matches a known case pattern or build dynamic factual run
    matched_case = None
    for c in get_all_test_cases():
        if query.lower() in c["input"].lower() or c["input"].lower() in query.lower():
            matched_case = c
            break

    if matched_case:
        run_data = EvaluationEngine.build_case_run(matched_case)
    else:
        # Generic evaluation run for custom input
        case_stub = {
            "id": "custom",
            "category": "correct_factual",
            "title": "Custom Verification",
            "input": query,
            "expected_decision": "ACCEPT",
            "expected_verification": "verified",
        }
        run_data = EvaluationEngine.build_case_run(case_stub)

    EvaluationEngine.set_latest(run_data)
    return run_data
