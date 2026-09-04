from redis.asyncio import Redis

_TAKE = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
return count <= tonumber(ARGV[1]) and 1 or 0
"""


class RedisRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        return bool(await self._redis.eval(_TAKE, 1, f"looksee:rate:{key}", limit, window_seconds))
