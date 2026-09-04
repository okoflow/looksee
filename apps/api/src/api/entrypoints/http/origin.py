import re

from starlette.datastructures import URL, Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class TrustedOriginMiddleware:
    def __init__(self, app: ASGIApp, allow_origin_regex: str) -> None:
        self._app = app
        self._allowed = re.compile(allow_origin_regex)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        protected = scope["type"] == "websocket" or (
            scope["type"] == "http" and scope["method"] not in {"GET", "HEAD", "OPTIONS"}
        )
        origin = Headers(scope=scope).get("origin") if protected else None
        if origin is not None and not self._is_allowed(origin, scope):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008, "reason": "untrusted origin"})
            else:
                response = JSONResponse({"detail": "untrusted origin"}, status_code=403)
                await response(scope, receive, send)
            return

        await self._app(scope, receive, send)

    def _is_allowed(self, origin: str, scope: Scope) -> bool:
        if self._allowed.fullmatch(origin):
            return True

        request_url = URL(scope=scope)
        scheme = {"ws": "http", "wss": "https"}.get(request_url.scheme, request_url.scheme)

        return origin == f"{scheme}://{request_url.netloc}"
