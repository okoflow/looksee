from typing import Protocol


class RateLimiter(Protocol):
    async def allow(self, key: str, *, limit: int, window_seconds: int) -> bool: ...
