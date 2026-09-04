from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from api.adapters.security import decode_session_token, issue_session_token
from api.adapters.security.keys import derive_key
from api.adapters.security.media import JwtMediaTokens
from api.application.media import MediaGrant


def test_media_and_session_tokens_are_not_interchangeable():
    codec = JwtMediaTokens()
    grant = MediaGrant(uuid4(), uuid4(), "read")
    media_token = codec.issue(grant)

    assert codec.decode(media_token) == grant
    assert decode_session_token(media_token) is None
    assert codec.decode(issue_session_token(grant.user_id)) is None


@pytest.mark.parametrize("claim", ["sub", "camera", "action", "aud", "iat", "exp"])
def test_missing_security_claims_are_rejected(claim):
    codec = JwtMediaTokens()
    token = codec.issue(MediaGrant(uuid4(), uuid4(), "read"))
    claims = jwt.decode(token, options={"verify_signature": False})
    del claims[claim]

    forged = jwt.encode(claims, derive_key(b"looksee.media"), algorithm="HS256")

    assert codec.decode(forged) is None


def test_expired_media_token_is_rejected():
    codec = JwtMediaTokens()
    token = codec.issue(MediaGrant(uuid4(), uuid4(), "read"))
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)

    expired = jwt.encode(claims, derive_key(b"looksee.media"), algorithm="HS256")

    assert codec.decode(expired) is None
