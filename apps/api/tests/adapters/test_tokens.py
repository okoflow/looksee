"""Signed session tokens: issue, verify, and reject anything tampered or expired."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from api.adapters.security.keys import session_signing_key
from api.adapters.security.tokens import SESSION_TTL, decode_session_token, issue_session_token


def test_issued_token_decodes_to_the_same_user():
    user_id = uuid4()

    assert decode_session_token(issue_session_token(user_id)) == user_id


def test_token_carries_the_session_ttl():
    claims = jwt.decode(issue_session_token(uuid4()), options={"verify_signature": False})

    assert claims["exp"] - claims["iat"] == int(SESSION_TTL.total_seconds())
    assert timedelta(days=7) == SESSION_TTL


def test_tampered_signature_is_rejected():
    header, payload, signature = issue_session_token(uuid4()).split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]

    assert decode_session_token(f"{header}.{payload}.{flipped}") is None


def test_token_signed_with_another_key_is_rejected():
    forged = jwt.encode(
        {"sub": str(uuid4())}, b"not-the-signing-key-but-long-enough", algorithm="HS256"
    )

    assert decode_session_token(forged) is None


def test_expired_token_is_rejected():
    past = datetime.now(UTC) - timedelta(days=8)
    expired = jwt.encode(
        {"sub": str(uuid4()), "iat": past, "exp": past + SESSION_TTL},
        session_signing_key(),
        algorithm="HS256",
    )

    assert decode_session_token(expired) is None


@pytest.mark.parametrize("claims", [{}, {"sub": "not-a-uuid"}, {"sub": 42}])
def test_token_without_a_valid_subject_is_rejected(claims):
    token = jwt.encode(claims, session_signing_key(), algorithm="HS256")

    assert decode_session_token(token) is None


def test_unsigned_token_is_rejected():
    unsigned = jwt.encode({"sub": str(uuid4())}, None, algorithm="none")

    assert decode_session_token(unsigned) is None


@pytest.mark.parametrize("garbage", ["", "abc", "a.b.c", "Bearer x"])
def test_garbage_is_rejected(garbage):
    assert decode_session_token(garbage) is None
