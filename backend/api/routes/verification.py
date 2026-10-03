from fastapi import APIRouter

from agents.verification_agent import run_verification
from schemas.verification import VerifyRequest, VerifyResponse

router = APIRouter()


@router.post("", response_model=VerifyResponse)
async def verify(body: VerifyRequest):
    question = body.question or "Verify the following claims."
    result = await run_verification(question, body.text, [], 2)
    return VerifyResponse(
        verification=result.get("verification") or {"performed": False},
        claims=result.get("claim_results") or [],
        sources=result.get("sources") or [],
        answer=body.text,
    )
