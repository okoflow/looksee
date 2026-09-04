"""Session-gated static file serving for snapshot evidence."""

from collections.abc import Awaitable, Callable
from http.cookies import CookieError, SimpleCookie
from uuid import UUID

from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from api.adapters.security import decode_session_token
from api.entrypoints.http.dependencies import SESSION_COOKIE


class AuthenticatedStaticFiles(StaticFiles):
    def __init__(self, *, user_exists: Callable[[UUID], Awaitable[bool]], **kwargs) -> None:
        super().__init__(**kwargs)
        self._user_exists = user_exists

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            user_id = _scope_user_id(scope)
            if user_id is None or not await self._user_exists(user_id):
                response = JSONResponse({"detail": "authentication required"}, status_code=401)
                await response(scope, receive, send)
                return

        await super().__call__(scope, receive, send)


def _scope_user_id(scope: Scope) -> UUID | None:
    headers = dict(scope.get("headers", ()))
    cookie_header = headers.get(b"cookie")
    if cookie_header is None:
        return None

    cookies = SimpleCookie()
    try:
        cookies.load(cookie_header.decode("latin-1"))
    except CookieError:
        return None
    morsel = cookies.get(SESSION_COOKIE)
    if morsel is None:
        return None

    return decode_session_token(morsel.value)
