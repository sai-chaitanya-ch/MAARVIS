from __future__ import annotations

from typing import Any, Dict

from agents.code_agent import run_code
from agents.critic_agent import run_critic
from agents.finalizer_agent import finalize
from agents.general_agent import run_general
from agents.logic_agent import run_logic
from agents.master_agent import route_intent
from agents.math_agent import run_math
from agents.rag_agent import run_rag
from agents.research_agent import run_research
from agents.verification_agent import run_verification
from config.settings import get_settings
from graph.state import ConversationState
from models.llm import LLMError, get_llm
from verification.decision import decide_gate
from utils.events import EventSpan, current_bus


def bus_from(state: ConversationState):
    return current_bus()


async def node_route(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)
    async with EventSpan(bus, "routing"):
        if state.get("marvis_route"):
            route_val = state["marvis_route"]
            requires_rag = route_val == "MULTI_AGENT_RAG" or bool(state.get("requires_rag"))
            requires_code = route_val == "DIRECT_SANDBOX" or bool(state.get("requires_code"))
            requires_math = bool(state.get("requires_math"))
            requires_web = bool(state.get("requires_web"))
            if route_val == "MULTI_AGENT" and state.get("web_enabled") is not False:
                requires_web = True
            if state.get("web_enabled") is False:
                requires_web = False
            requires_verification = route_val in {"MULTI_AGENT", "MULTI_AGENT_RAG"}
            task_type = (
                "document" if requires_rag
                else ("code" if requires_code
                else ("math" if requires_math
                else ("conversation" if route_val == "DIRECT_FAST" else "factual")))
            )
            return {
                "intent": f"MARVIS triage: {route_val}",
                "task_type": task_type,
                "requires_web": requires_web,
                "requires_rag": requires_rag,
                "requires_math": requires_math,
                "requires_code": requires_code,
                "requires_verification": requires_verification,
                "verification_level": 2 if requires_verification else 0,
            }

        route = await route_intent(
            state["user_message"],
            state.get("document_ids"),
            state.get("code"),
        )
        if state.get("web_enabled") is False:
            route["requires_web"] = False
    return {
        "intent": route.get("reason"),
        "task_type": route["task_type"],
        "requires_web": route["requires_web"],
        "requires_rag": route["requires_rag"],
        "requires_math": route["requires_math"],
        "requires_code": route["requires_code"],
        "requires_verification": route["requires_verification"],
        "verification_level": route["verification_level"],
    }


async def node_general(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)
    async with EventSpan(bus, "generating"):
        if state.get("task_type") == "reasoning":
            answer = await run_logic(state["user_message"])
        else:
            async def on_token(chunk: str):
                await bus.token(chunk)

            answer = await run_general(
                state["user_message"],
                state.get("messages") or [],
                on_token=on_token,
            )
    return {"draft_answer": answer}



async def node_research(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)

    async def cb(event: str, detail: str = "") -> None:
        await bus.emit(event, "started", detail=detail)
        await bus.emit(event, "completed", detail=detail)

    # Check if web search is available before calling
    try:
        try:
            from services.provider_service import get_web_search_credentials
        except ImportError:
            from backend.services.provider_service import get_web_search_credentials
        web_cred = get_web_search_credentials()
    except Exception:
        web_cred = None

    if not web_cred and not get_settings().tavily_api_key:
        # Web search unavailable: degrade gracefully by answering from model knowledge
        await bus.emit("web_search", "skipped", detail="Web search unavailable; answering from model knowledge")
        async with EventSpan(bus, "generating"):
            answer = await run_general(state["user_message"], state.get("messages") or [])
        return {
            "draft_answer": answer,
            "research_results": {"web_search_available": False, "skipped": True},
            "sources": [],
        }

    try:
        result = await run_research(state["user_message"], event_cb=cb)
    except Exception as exc:
        await bus.emit("web_search", "failed", detail=str(exc))
        # Graceful fallback to model knowledge on web search failure
        async with EventSpan(bus, "generating"):
            answer = await run_general(state["user_message"], state.get("messages") or [])
        return {
            "draft_answer": answer,
            "research_results": {"web_search_available": False, "error": str(exc)},
            "sources": [],
            "errors": [str(exc)],
        }
    return {
        "draft_answer": result["draft_answer"],
        "research_results": result,
        "sources": result.get("sources") or [],
    }


async def node_rag(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)
    doc_ids = state.get("document_ids") or []
    user_id = state.get("user_id") or "default_user"
    if not doc_ids:
        return {
            "draft_answer": "No documents were attached to this query.",
            "document_context": [],
            "sources": [],
        }
    async with EventSpan(bus, "retrieval"):
        try:
            result = await run_rag(state["user_message"], doc_ids, user_id=user_id)
        except Exception as exc:
            await bus.emit("retrieval", "failed", detail=str(exc))
            return {
                "draft_answer": f"Document retrieval could not be completed: {exc}",
                "document_context": [],
                "errors": [str(exc)],
            }
    if result.get("rag_failed"):
        return result
    await bus.emit("reranking", "completed")
    return {
        "draft_answer": result["draft_answer"],
        "document_context": result.get("document_context") or [],
        "sources": result.get("sources") or [],
    }


async def node_math(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)
    async with EventSpan(bus, "calculation"):
        result = run_math(state["user_message"])
    out: Dict[str, Any] = {
        "draft_answer": result["draft_answer"],
        "final_answer": result["draft_answer"],
        "calculation_result": result.get("calculation_result"),
        "skip_llm_finalize": True,
    }
    if result.get("tool_verification"):
        out["verification"] = result["tool_verification"]
        out["claims"] = result.get("claims") or []
        out["claim_results"] = result.get("claims") or []
        out["sources"] = result.get("sources") or []
    return out


async def node_code(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)
    async with EventSpan(bus, "code_execution"):
        result = await run_code(state["user_message"], state.get("code"), state.get("language"))
    sources = []
    code_result = result.get("code_result")
    if code_result and code_result.get("executed"):
        sources.append(
            {
                "id": "sandbox",
                "title": "Docker sandbox",
                "url": None,
                "source_type": "code_execution",
                "evidence": f"exit_code={code_result.get('exit_code')}\n{code_result.get('output')}",
            }
        )
    return {
        "draft_answer": result["draft_answer"],
        "code_result": code_result,
        "sources": sources,
    }


async def node_gate(state: ConversationState) -> Dict[str, Any]:
    if (
        state.get("marvis_route") in {"DIRECT_FAST", "DIRECT_SANDBOX"}
        or state.get("requires_verification") is False
        or state.get("skip_llm_finalize")
    ):
        return {
            "gate_decision": "NOT_REQUIRED",
            "verification_level": 0,
            "requires_verification": False,
        }
    if state.get("marvis_route") in {"MULTI_AGENT", "MULTI_AGENT_RAG"} and state.get("requires_verification"):
        return {
            "gate_decision": "REQUIRED",
            "verification_level": 2,
            "requires_verification": True,
        }
    decision = decide_gate(
        state.get("task_type") or "conversation",
        bool(state.get("requires_web")),
        state["user_message"],
    )
    if state.get("skip_llm_finalize"):
        decision["decision"] = "NOT_REQUIRED"
    return {
        "gate_decision": decision["decision"],
        "verification_level": decision["level"],
        "requires_verification": decision["decision"] != "NOT_REQUIRED",
    }


async def node_verify(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)

    async def cb(event: str, detail: str = "") -> None:
        await bus.emit(event, "started", detail=detail)
        await bus.emit(event, "completed", detail=detail)

    allow_web = bool(state.get("requires_web") and state.get("web_enabled") is not False)
    try:
        result = await run_verification(
            state["user_message"],
            state.get("draft_answer") or "",
            state.get("sources") or [],
            int(state.get("verification_level") or 1),
            allow_web=allow_web,
            event_cb=cb,
        )
    except Exception as exc:
        await bus.emit("verification", "failed", detail=str(exc))
        from verification.confidence import build_verification_payload

        return {
            "verification": build_verification_payload(
                True, [], None, state.get("verification_level"), error=str(exc), independent_completed=False
            ),
            "errors": [str(exc)],
        }
    await bus.verification(result.get("verification") or {})
    merged_sources = result.get("sources") or state.get("sources") or []
    await bus.sources(merged_sources)
    return {
        "claims": result.get("claims") or [],
        "claim_results": result.get("claim_results") or [],
        "evidence": result.get("evidence") or [],
        "contradictions": result.get("contradictions") or {},
        "verification": result.get("verification") or {"performed": False},
        "sources": merged_sources,
    }


async def node_critic(state: ConversationState) -> Dict[str, Any]:
    if int(state.get("verification_level") or 0) < 3:
        return {"critic_result": {"ok": True, "issues": [], "summary": "Critic skipped for this verification level."}}
    bus = bus_from(state)
    async with EventSpan(bus, "critic"):
        critic = await run_critic(
            state["user_message"],
            state.get("draft_answer") or "",
            state.get("claim_results") or [],
            state.get("contradictions") or {},
            state.get("sources") or [],
        )
    return {"critic_result": critic}


async def node_correct(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)
    settings = get_settings()
    count = int(state.get("correction_count") or 0) + 1
    if count > settings.max_verification_iterations:
        return {"correction_count": count}
    async with EventSpan(bus, "correction"):
        llm = get_llm()
        import json
        from security.validation import wrap_untrusted

        corrected = await llm.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "Revise the draft so it only states what evidence supports. "
                        "Qualify PARTIALLY_SUPPORTED claims, correct CONTRADICTED claims, "
                        "and remove or hedge INSUFFICIENT_EVIDENCE claims. "
                        "Preserve uncertainty. Do not invent sources."
                    ),
                },
                {
                    "role": "user",
                    "content": wrap_untrusted(
                        "revision_bundle",
                        json.dumps(
                            {
                                "question": state["user_message"],
                                "draft": state.get("draft_answer"),
                                "claim_results": state.get("claim_results"),
                                "contradictions": state.get("contradictions"),
                                "critic": state.get("critic_result"),
                            }
                        )[:14000],
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=1600,
        )
    return {"draft_answer": corrected, "correction_count": count}


async def node_finalize(state: ConversationState) -> Dict[str, Any]:
    bus = bus_from(state)
    skip_finalize = (
        state.get("skip_llm_finalize")
        or (
            (state.get("critic_result") or {}).get("ok", True)
            and not (state.get("contradictions") or {}).get("has_conflict")
            and int(state.get("correction_count") or 0) == 0
        )
    )

    if skip_finalize:
        answer = state.get("final_answer") or state.get("draft_answer") or ""
        note = (state.get("verification") or {}).get("note")
        if note and note not in answer:
            answer = f"{answer}\n\n{note}"
        async with EventSpan(bus, "finalization"):
            pass
        return {"final_answer": answer, "agent_events": bus.events}

    async with EventSpan(bus, "finalization"):
        try:
            answer = await finalize(
                state["user_message"],
                state.get("draft_answer") or "",
                state.get("claim_results"),
                state.get("contradictions"),
                state.get("critic_result"),
                state.get("sources"),
            )
        except LLMError as exc:
            answer = state.get("draft_answer") or f"The model could not complete a response: {exc}"
            errors = list(state.get("errors") or []) + [str(exc)]
            return {"final_answer": answer, "errors": errors, "agent_events": bus.events}
    note = (state.get("verification") or {}).get("note")
    performed = (state.get("verification") or {}).get("performed")
    if performed and note and note not in answer:
        answer = f"{answer}\n\n{note}"
    return {"final_answer": answer, "agent_events": bus.events}
