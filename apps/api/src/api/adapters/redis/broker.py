"""Shared FastStream Redis connection."""

from faststream.redis import RedisBroker

from api.config import settings

broker = RedisBroker(settings.redis_url)
