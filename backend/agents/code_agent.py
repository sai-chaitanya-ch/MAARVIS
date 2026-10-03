from __future__ import annotations

import re
from typing import Any, Dict, Optional

from models.llm import get_llm
from config.settings import get_settings
from tools.code_executor import code_execute

SYSTEM = """You are a careful code analyst for MAARVIS.
Languages: Java, Python, JavaScript/TypeScript, C, C++.
Explain correctness, bugs, edge cases, and suggest a corrected version when needed.
If execution results are provided, treat them as ground truth for runtime behavior.
Never claim code was executed if execution results are missing.
Do not mention internal agent names.
Return a natural answer, not JSON.
"""

DETECT = """Identify the programming language and whether the snippet is executable as-is.
Return JSON: {"language":"python|javascript|typescript|java|c|cpp|unknown","executable":true,"code":"..."}
Extract only the code if the user mixed prose and code.
"""


async def run_code(question: str, code: Optional[str], language: Optional[str]) -> Dict[str, Any]:
    llm = get_llm()
    settings = get_settings()
    snippet = code or _extract_fence(question) or question
    meta_raw = await llm.complete(
        [
            {"role": "system", "content": DETECT},
            {"role": "user", "content": snippet[:12000]},
        ],
        temperature=0,
        max_tokens=800,
        json_mode=True,
    )
    import json

    try:
        meta = json.loads(meta_raw)
    except json.JSONDecodeError:
        meta = {"language": language or "python", "executable": False, "code": snippet}
    lang = (language or meta.get("language") or "python").lower()
    extracted = meta.get("code") or snippet
    execution = None
    if meta.get("executable") and lang in {"python", "javascript", "typescript", "java", "c", "cpp", "c++"}:
        execution = await code_execute(extracted, lang)
    extra = ""
    if execution:
        if execution.get("executed"):
            extra = (
                f"\nSandbox execution:\nexit_code={execution.get('exit_code')}\noutput:\n{execution.get('output')}"
            )
        else:
            extra = f"\nSandbox did not run: {execution.get('error')}. Do not claim the code was executed."
    answer = await llm.complete(
        [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"User question:\n{question}\n\nCode:\n{extracted}\n{extra}",
            },
        ],
        temperature=0.1,
        max_tokens=1600,
    )
    return {
        "draft_answer": answer,
        "code_result": execution,
        "language": lang,
    }


def _extract_fence(text: str) -> Optional[str]:
    match = re.search(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)```", text, re.S)
    if match:
        return match.group(1).strip()
    return None
