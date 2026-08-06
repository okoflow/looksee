"""Shared outbound HTTP client with connection pooling.

Opened once per process and closed in the app's lifespan; callers pass
per-request timeouts. Avoids a fresh TCP/TLS handshake per delivery on the
hot event path (webhook/telegram) and per mediamtx control-plane call.
"""

from __future__ import annotations

import httpx

client = httpx.AsyncClient()


async def close_client() -> None:
    await client.aclose()
