from tools.calculator import is_incomplete_expression, looks_like_math, parse_math_query
from agents.master_agent import heuristic_route
from verification.scoring import overall_status, score_claims
from verification.decision import decide_gate
from schemas.chat import VerificationStatus


def test_math_17_times_24():
    result = parse_math_query("17 * 24")
    assert result.value == 408
    assert result.incomplete is False


def test_math_equation_verified():
    result = parse_math_query("Is 17 * 24 = 408?")
    assert result.comparison is True
    assert result.value == 408


def test_incomplete_math_not_contradiction():
    assert is_incomplete_expression("2 + 3 =")
    result = parse_math_query("2 + 3 =")
    assert result.incomplete is True
    assert result.comparison is None


def test_greeting_route():
    route = heuristic_route("Hi")
    assert route["task_type"] == "conversation"
    assert route["requires_verification"] is False
    assert route["requires_web"] is False


def test_latest_python_route():
    route = heuristic_route("What is the latest version of Python?")
    assert route["requires_web"] is True
    assert route["requires_verification"] is True


def test_research_route():
    route = heuristic_route("Research the latest AI agent frameworks.")
    assert route["task_type"] == "research"


def test_scoring_no_invention():
    score, counts, metrics = score_claims(
        [
            {"status": "SUPPORTED"},
            {"status": "SUPPORTED"},
            {"status": "PARTIALLY_SUPPORTED"},
            {"status": "INSUFFICIENT_EVIDENCE"},
        ]
    )
    assert score == 0.5
    assert counts["supported"] == 2
    assert counts["partial"] == 1
    assert counts["unverified"] == 1
    assert metrics["verified"] == 50
    assert metrics["partiallyVerified"] == 25
    assert metrics["unverified"] == 25
    assert metrics["conflicting"] == 0
    assert overall_status([{"status": "SUPPORTED"}]) == VerificationStatus.VERIFIED


def test_verification_case_1_all_verified():
    # TEST 1: 5/5 verified -> Expected: Verified 100%
    from verification.confidence import build_verification_payload
    claims = [{"status": "SUPPORTED"} for _ in range(5)]
    res = build_verification_payload(True, claims, independent_completed=True)
    assert res["status"] == "verified"
    assert res["independentVerificationCompleted"] is True
    assert res["metrics"]["verified"] == 100
    assert res["metrics"]["conflicting"] == 0


def test_verification_case_2_partial():
    # TEST 2: 3/5 verified, 1/5 partially verified, 1/5 unverified -> Expected: Verified 60%, Partially Verified 20%, Unverified 20%
    from verification.confidence import build_verification_payload
    claims = [
        {"status": "SUPPORTED"},
        {"status": "SUPPORTED"},
        {"status": "SUPPORTED"},
        {"status": "PARTIALLY_SUPPORTED"},
        {"status": "INSUFFICIENT_EVIDENCE"},
    ]
    res = build_verification_payload(True, claims, independent_completed=True)
    assert res["status"] == "partially_verified"
    assert res["metrics"]["verified"] == 60
    assert res["metrics"]["partiallyVerified"] == 20
    assert res["metrics"]["unverified"] == 20
    assert res["metrics"]["conflicting"] == 0


def test_verification_case_3_never_completed():
    # TEST 3: Verification never completed -> Expected: None / dash metrics, Status: verification_incomplete
    from verification.confidence import build_verification_payload
    res = build_verification_payload(True, [], independent_completed=False, error="Timeout")
    assert res["status"] == "verification_incomplete"
    assert res["independentVerificationCompleted"] is False
    assert res["metrics"]["verified"] is None
    assert res["note"] == "Independent verification could not be completed."


def test_verification_case_4_no_evidence_evaluated():
    # TEST 4: No evidence found and claims evaluated -> Expected: Verified 0%, Unverified 100%
    from verification.confidence import build_verification_payload
    claims = [
        {"status": "INSUFFICIENT_EVIDENCE"},
        {"status": "INSUFFICIENT_EVIDENCE"},
    ]
    res = build_verification_payload(True, claims, independent_completed=True)
    assert res["status"] == "unverified"
    assert res["metrics"]["verified"] == 0
    assert res["metrics"]["unverified"] == 100


def test_verification_case_5_conflicting_evidence():
    # TEST 5: Conflicting evidence detected -> Expected: Conflicting > 0%, Status: conflicting
    from verification.confidence import build_verification_payload
    claims = [
        {"status": "SUPPORTED"},
        {"status": "CONTRADICTED"},
    ]
    res = build_verification_payload(True, claims, independent_completed=True)
    assert res["status"] == "conflicting"
    assert res["metrics"]["conflicting"] > 0


def test_verification_case_6_failed_cannot_be_100_percent():
    # TEST 6: LLM generated a confident answer but independent verification failed -> NOT Verified 100%, Expected status: verification_incomplete
    from verification.confidence import build_verification_payload
    res = build_verification_payload(True, [], independent_completed=False, error="API unreachable")
    assert res["status"] == "verification_incomplete"
    assert res["metrics"]["verified"] != 100
    assert res["metrics"]["verified"] is None


def test_gate_skips_greeting():
    decision = decide_gate("conversation", False, "Hi")
    assert decision["decision"] == "NOT_REQUIRED"


def test_looks_like_math():
    assert looks_like_math("17 * 24")
    assert not looks_like_math("Explain recursion")
