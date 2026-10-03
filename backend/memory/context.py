from __future__ import annotations

from typing import Any, Dict, List


def build_context_messages(history: List[Dict[str, str]], user_message: str, extra: str = "") -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    for item in history[-10:]:
        role = item.get("role")
        if role not in {"user", "assistant"}:
            continue
        messages.append({"role": role, "content": item.get("content", "")})
    content = user_message
    if extra:
        content = f"{user_message}\n\n{extra}"
    messages.append({"role": "user", "content": content})
    return messages
