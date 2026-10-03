from typing import Any, Awaitable, Callable, TypeVar

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.4, min=0.4, max=4),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    ):
        with attempt:
            return await fn()
    raise RuntimeError("retry_async exhausted without result")
