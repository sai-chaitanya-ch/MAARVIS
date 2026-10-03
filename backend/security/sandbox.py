from __future__ import annotations

import tempfile
import uuid
from typing import Any, Dict, Optional

from config.settings import get_settings


LANGUAGE_IMAGES = {
    "python": "python:3.11-alpine",
    "javascript": "node:20-alpine",
    "typescript": "node:20-alpine",
    "java": "eclipse-temurin:17-jdk-alpine",
    "c": "gcc:13",
    "cpp": "gcc:13",
    "c++": "gcc:13",
}

FORBIDDEN = [
    "rm -rf",
    "mkfs",
    "dd if=",
    ":(){",
    "shutdown",
    "reboot",
    "curl ",
    "wget ",
    "nc -",
    "ncat",
    "/etc/passwd",
    "docker ",
]


class SandboxError(Exception):
    pass


class SandboxUnavailable(SandboxError):
    pass


def _reject_dangerous(code: str) -> None:
    lowered = code.lower()
    for token in FORBIDDEN:
        if token in lowered:
            raise SandboxError(f"Code rejected: contains disallowed pattern '{token.strip()}'")


def run_in_sandbox(code: str, language: str, stdin: str = "") -> Dict[str, Any]:
    settings = get_settings()
    lang = language.lower().strip()
    if lang not in LANGUAGE_IMAGES:
        raise SandboxError(f"Unsupported language: {language}")
    _reject_dangerous(code)

    try:
        import docker  # type: ignore
        from docker.errors import DockerException, ImageNotFound  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SandboxUnavailable("Docker SDK is not installed") from exc

    try:
        client = docker.from_env()
        client.ping()
    except Exception as exc:
        raise SandboxUnavailable("Docker is not available. Code was not executed.") from exc

    workdir = tempfile.mkdtemp(prefix="verify-sandbox-")
    filename, command = _prepare_files(workdir, code, lang)
    name = f"verify-sbx-{uuid.uuid4().hex[:12]}"
    try:
        try:
            client.images.get(LANGUAGE_IMAGES[lang])
        except ImageNotFound:
            client.images.pull(LANGUAGE_IMAGES[lang])
        container = client.containers.run(
            LANGUAGE_IMAGES[lang],
            command=command,
            name=name,
            detach=True,
            network_disabled=True,
            mem_limit=settings.code_memory_limit,
            nano_cpus=int(settings.code_cpu_limit * 1_000_000_000),
            pids_limit=64,
            user="65534:65534",
            working_dir="/work",
            volumes={workdir: {"bind": "/work", "mode": "ro"}},
            stdout=True,
            stderr=True,
            stdin_open=False,
        )
        result = container.wait(timeout=settings.code_execution_timeout)
        logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
        status = int(result.get("StatusCode", 1))
        return {
            "executed": True,
            "exit_code": status,
            "output": logs[-8000:],
            "language": lang,
            "filename": filename,
        }
    except Exception as exc:
        raise SandboxError(f"Sandbox execution failed: {exc}") from exc
    finally:
        try:
            existing = client.containers.get(name)
            existing.remove(force=True)
        except Exception:
            pass
        try:
            import shutil

            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            pass


def _prepare_files(workdir: str, code: str, lang: str) -> tuple[str, list[str]]:
    from pathlib import Path

    mapping = {
        "python": ("main.py", ["python", "/work/main.py"]),
        "javascript": ("main.js", ["node", "/work/main.js"]),
        "typescript": ("main.ts", ["node", "/work/main.ts"]),
        "java": None,
        "c": None,
        "cpp": None,
        "c++": None,
    }
    if lang in {"python", "javascript", "typescript"}:
        filename, command = mapping[lang]  # type: ignore[misc]
        Path(workdir, filename).write_text(code, encoding="utf-8")
        return filename, command
    if lang == "java":
        Path(workdir, "Main.java").write_text(code, encoding="utf-8")
        return "Main.java", ["sh", "-c", "javac /work/Main.java && java -cp /work Main"]
    if lang in {"c", "cpp", "c++"}:
        src = "main.c" if lang == "c" else "main.cpp"
        compiler = "gcc" if lang == "c" else "g++"
        Path(workdir, src).write_text(code, encoding="utf-8")
        return src, ["sh", "-c", f"{compiler} /work/{src} -o /tmp/a.out && /tmp/a.out"]
    raise SandboxError("Unsupported language")
