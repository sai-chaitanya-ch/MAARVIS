from __future__ import annotations

from typing import Any, Dict, Optional

from security.sandbox import SandboxError, SandboxUnavailable, run_in_sandbox


async def code_execute(code: str, language: str, stdin: str = "") -> Dict[str, Any]:
    try:
        result = run_in_sandbox(code, language, stdin)
        result["error"] = None
        return result
    except SandboxUnavailable as exc:
        return {
            "executed": False,
            "exit_code": None,
            "output": None,
            "language": language,
            "error": str(exc),
        }
    except SandboxError as exc:
        return {
            "executed": False,
            "exit_code": None,
            "output": None,
            "language": language,
            "error": str(exc),
        }
