"""Session-gated static file serving for snapshot evidence."""

from http.cookies import SimpleCookie

from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from api.adapters.security import decode_session_token
from api.entrypoints.http.dependencies import SESSION_COOKIE


class AuthenticatedStaticFiles(StaticFiles):
    """Serve files only to requests carrying a valid session cookie.

    Snapshots are immutable evidence images, so the signature check alone is
    enough here; a deleted user's cookie stops working when its token expires.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not _scope_authenticated(scope):
            response = JSONResponse({"detail": "authentication required"}, status_code=401)
            await response(scope, receive, send)
            return

        await super().__call__(scope, receive, send)


def _scope_authenticated(scope: Scope) -> bool:
    headers = dict(scope.get("headers", ()))
    cookie_header = headers.get(b"cookie")
    if cookie_header is None:
        return False

    cookies = SimpleCookie()
    cookies.load(cookie_header.decode("latin-1"))
    morsel = cookies.get(SESSION_COOKIE)
    if morsel is None:
        return False

    return decode_session_token(morsel.value) is not None
