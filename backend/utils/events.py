from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from contextvars import ContextVar

from schemas.chat import AgentEvent
from utils.tracing import Timer

bus_var: ContextVar["EventBus | None"] = ContextVar("event_bus", default=None)


Listener = Callable[[Dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._listeners: List[Listener] = []
        self.events: List[Dict[str, Any]] = []

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    async def emit(self, event: str, status: str, *, detail: Optional[str] = None, duration_ms: Optional[int] = None, **metadata: Any) -> Dict[str, Any]:
        payload = AgentEvent(
            event=event,
            status=status,
            detail=detail,
            duration_ms=duration_ms,
            metadata={k: v for k, v in metadata.items() if v is not None},
        ).model_dump(mode="json")
        self.events.append(payload)
        for listener in self._listeners:
            await listener({"type": "activity", **payload})
        return payload

    async def token(self, content: str) -> None:
        for listener in self._listeners:
            await listener({"type": "token", "content": content})

    async def verification(self, payload: Dict[str, Any]) -> None:
        for listener in self._listeners:
            await listener({"type": "verification", **payload})

    async def sources(self, sources: List[Dict[str, Any]]) -> None:
        for listener in self._listeners:
            await listener({"type": "sources", "sources": sources})

    async def complete(self, payload: Dict[str, Any]) -> None:
        for listener in self._listeners:
            await listener({"type": "complete", **payload})

    async def error(self, message: str) -> None:
        for listener in self._listeners:
            await listener({"type": "error", "message": message})


def current_bus() -> EventBus:
    bus = bus_var.get()
    if bus is None:
        bus = EventBus()
        bus_var.set(bus)
    return bus


class EventSpan:
    def __init__(self, bus: EventBus, event: str, detail: Optional[str] = None) -> None:
        self.bus = bus
        self.event = event
        self.detail = detail
        self.timer = Timer()

    async def __aenter__(self) -> EventSpan:
        await self.bus.emit(self.event, "started", detail=self.detail)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        status = "failed" if exc else "completed"
        detail = str(exc) if exc else self.detail
        await self.bus.emit(self.event, status, detail=detail, duration_ms=self.timer.ms())
