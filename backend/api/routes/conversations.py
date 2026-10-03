from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from memory.conversation import (
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
)
from schemas.chat import ConversationDetail, ConversationSummary
from security.auth import get_current_user_id

router = APIRouter()


class NewConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"


@router.post("", response_model=Dict[str, Any])
async def create_new_conversation(
    body: Optional[NewConversationRequest] = None,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    user_id = await get_current_user_id(request, authorization, x_user_id)
    title = (body.title if body and body.title else "New Conversation")[:80]
    cid = await create_conversation(title, user_id=user_id)
    return {"id": cid, "title": title, "user_id": user_id}


@router.get("", response_model=List[ConversationSummary])
async def conversations(
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    user_id = await get_current_user_id(request, authorization, x_user_id)
    rows = await list_conversations(user_id=user_id)
    return [
        ConversationSummary(
            id=r["id"],
            title=r["title"],
            updated_at=r["updated_at"],
            message_count=r["message_count"],
        )
        for r in rows
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def conversation(
    conversation_id: str,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    user_id = await get_current_user_id(request, authorization, x_user_id)
    data = await get_conversation(conversation_id, user_id=user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = []
    for m in data.get("messages", []):
        exec_trace = m.get("execution_trace")
        messages.append(
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "provider": m.get("provider"),
                "model": m.get("model"),
                "execution_id": m.get("execution_id"),
                "routing": m.get("routing"),
                "verification": m.get("verification"),
                "execution_trace": exec_trace,
                "capabilities": (exec_trace or {}).get("capabilities"),
                "recommendations": (exec_trace or {}).get("recommendations"),
                "sources": m.get("sources") or [],
                "events": m.get("events") or [],
                "claims": m.get("claims") or [],
                "created_at": m["created_at"],
            }
        )

    return ConversationDetail(
        id=data["id"],
        title=data["title"],
        messages=messages,
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


@router.delete("/{conversation_id}")
async def remove_conversation(
    conversation_id: str,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    user_id = await get_current_user_id(request, authorization, x_user_id)
    ok = await delete_conversation(conversation_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "id": conversation_id}
