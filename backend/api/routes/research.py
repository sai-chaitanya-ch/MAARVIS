from fastapi import APIRouter, HTTPException

from agents.research_agent import run_research
from agents.verification_agent import run_verification
from schemas.research import ResearchRequest, ResearchResponse
from tools.web_search import TavilyError

router = APIRouter()


@router.post("", response_model=ResearchResponse)
async def research(body: ResearchRequest):
    try:
        result = await run_research(body.query)
    except TavilyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    verification = {"performed": False}
    if result.get("sources") and not result.get("research_failed"):
        verified = await run_verification(body.query, result["draft_answer"], result["sources"], 2)
        verification = verified.get("verification") or verification
        sources = verified.get("sources") or result.get("sources")
    else:
        sources = result.get("sources") or []
    return ResearchResponse(
        query=body.query,
        answer=result.get("draft_answer") or "",
        sources=sources,
        verification=verification,
    )
