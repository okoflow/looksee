"""Stateless session tokens: signed JWTs carried in an httpOnly cookie."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from api.adapters.security.keys import session_signing_key

SESSION_TTL = timedelta(days=7)

_ALGORITHM = "HS256"


def issue_session_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    claims = {"sub": str(user_id), "iat": now, "exp": now + SESSION_TTL}

    return jwt.encode(claims, session_signing_key(), algorithm=_ALGORITHM)


def decode_session_token(token: str) -> UUID | None:
    """Return the session's user id, or None for any invalid or expired token."""
    try:
        claims = jwt.decode(token, session_signing_key(), algorithms=[_ALGORITHM])

        return UUID(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
