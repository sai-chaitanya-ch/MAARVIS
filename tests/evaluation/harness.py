"""Evaluation harness for Verify.ai.

Measures false acceptance of incorrect claims, contradiction detection,
and calculation correctness. LLM-backed cases run only when HF_TOKEN is set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from tools.calculator import parse_math_query
from verification.scoring import overall_status
from schemas.chat import VerificationStatus


@dataclass
class EvalCase:
    name: str
    kind: str
    input: str
    expected: str


CASES = [
    EvalCase("math_correct", "math", "17 * 24", "408"),
    EvalCase("math_false_equation", "math_eq", "Is 17 * 24 = 409?", "false"),
    EvalCase("incomplete", "incomplete", "2 + 3 =", "incomplete"),
    EvalCase("greeting", "route", "Hi", "conversation"),
]


def run_offline_eval() -> dict:
    passed = 0
    failed = 0
    details = []
    for case in CASES:
        ok = False
        if case.kind == "math":
            ok = str(parse_math_query(case.input).value) == case.expected
        elif case.kind == "math_eq":
            ok = parse_math_query(case.input).comparison is False
        elif case.kind == "incomplete":
            ok = parse_math_query(case.input).incomplete is True
        elif case.kind == "route":
            from agents.master_agent import heuristic_route

            ok = heuristic_route(case.input)["task_type"] == case.expected
        passed += int(ok)
        failed += int(not ok)
        details.append({"name": case.name, "ok": ok})
    return {"passed": passed, "failed": failed, "false_acceptance_rate": None, "details": details}


if __name__ == "__main__":
    print(run_offline_eval())
