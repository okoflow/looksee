from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from api.adapters.security.keys import derive_key
from api.application.media import MediaGrant

MEDIA_TOKEN_TTL = timedelta(minutes=5)
_AUDIENCE = "looksee.media"


class JwtMediaTokens:
    def issue(self, grant: MediaGrant) -> str:
        now = datetime.now(UTC)

        return jwt.encode(
            {
                "sub": str(grant.user_id),
                "camera": str(grant.camera_id),
                "action": grant.action,
                "aud": _AUDIENCE,
                "iat": now,
                "exp": now + MEDIA_TOKEN_TTL,
            },
            derive_key(b"looksee.media"),
            algorithm="HS256",
        )

    def decode(self, token: str) -> MediaGrant | None:
        try:
            claims = jwt.decode(
                token,
                derive_key(b"looksee.media"),
                algorithms=["HS256"],
                audience=_AUDIENCE,
                options={"require": ["sub", "camera", "action", "aud", "iat", "exp"]},
            )
            action = claims["action"]
            if action not in ("read", "publish"):
                return None

            return MediaGrant(UUID(claims["sub"]), UUID(claims["camera"]), action)
        except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
            return None
