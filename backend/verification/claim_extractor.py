from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from models.llm import get_llm
from security.validation import wrap_untrusted

SYSTEM = """You extract independently verifiable factual claims from an assistant answer.
Return JSON: {"claims": [{"claim_text": "...", "claim_type": "date|statistic|named_entity|scientific|news|technical|other", "importance": "high|medium|low", "verification_required": true}]}
Rules:
- Extract only checkable facts (dates, versions, people, numbers, events, product claims).
- Do not extract opinions, greetings, explanations of well-known concepts, or creative writing.
- Do not extract the user's question as a claim unless the answer asserts it as fact.
- If there are no verifiable claims, return {"claims": []}.
- Never invent claims that are not in the answer.
"""


async def extract_claims(answer: str, question: str) -> List[Dict[str, Any]]:
    llm = get_llm()
    content = await llm.complete(
        [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": wrap_untrusted("answer", f"Question:\n{question}\n\nAnswer:\n{answer}"),
            },
        ],
        temperature=0,
        max_tokens=800,
        json_mode=True,
    )
    data = _parse_json(content)
    claims = []
    for index, item in enumerate(data.get("claims") or []):
        text = (item.get("claim_text") or "").strip()
        if not text:
            continue
        claims.append(
            {
                "claim_id": f"c{index+1}",
                "claim_text": text,
                "claim_type": item.get("claim_type") or "other",
                "importance": item.get("importance") or "medium",
                "verification_required": bool(item.get("verification_required", True)),
                "source_requirements": "independent web evidence",
            }
        )
    return claims


def _parse_json(text: str) -> Dict[str, Any]:
    """Parse potentially malformed / truncated JSON from LLM output."""
    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract the outermost {...} block
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # 3. Lenient repair: strip trailing commas before ] or }
            fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
            # Close any unclosed arrays / objects (common with truncated output)
            open_sq = fixed.count("[") - fixed.count("]")
            open_cu = fixed.count("{") - fixed.count("}")
            if open_sq > 0 or open_cu > 0:
                fixed = fixed.rstrip().rstrip(",")
                fixed += "]" * max(0, open_sq)
                fixed += "}" * max(0, open_cu)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    return {"claims": []}
