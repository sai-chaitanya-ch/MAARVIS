from __future__ import annotations

from models.llm import get_llm

SYSTEM = """You are a careful reasoning assistant.
Think through the user's problem step by step internally, but only output a clear final explanation.
Do not expose hidden chain-of-thought labels or agent names.
If a conclusion is uncertain, say so.
"""


async def run_logic(question: str) -> str:
    llm = get_llm()
    return await llm.complete(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ],
        temperature=0.2,
        max_tokens=1600,
    )
