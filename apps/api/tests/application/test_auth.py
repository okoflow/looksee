"""Owner setup, login, and session-user lookup against an in-memory session."""

import pytest

from api.adapters.persistence.models import User
from api.adapters.security import verify_password
from api.application import auth
from api.application.errors import InvalidCredentialsError, ResourceConflictError


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Owner@Example.com", "owner@example.com"),
        ("  owner@example.com  ", "owner@example.com"),
        ("owner@example.com", "owner@example.com"),
    ],
)
def test_normalize_email_lowercases_and_strips(raw, expected):
    assert auth.normalize_email(raw) == expected


async def test_requires_setup_until_first_user_exists(fake_session):
    before = await auth.requires_setup(fake_session)

    fake_session.seed(User(email="owner@example.com", name="Owner", password_hash="x"))
    after = await auth.requires_setup(fake_session)

    assert before is True
    assert after is False


async def test_create_owner_persists_normalized_email_and_hashed_password(fake_session):
    owner = await auth.create_owner(
        fake_session, email=" Owner@Example.com ", name="Owner", password="Secret123"
    )

    assert owner.email == "owner@example.com"
    assert owner.role == "owner"
    assert owner.password_hash != "Secret123"
    assert verify_password("Secret123", owner.password_hash)
    assert fake_session.commits == 1


async def test_create_owner_refuses_a_second_owner(fake_session):
    await auth.create_owner(fake_session, email="a@example.com", name="A", password="Secret123")

    with pytest.raises(ResourceConflictError, match="already set up"):
        await auth.create_owner(fake_session, email="b@example.com", name="B", password="Secret123")

    assert len(fake_session.rows[User]) == 1


async def test_authenticate_matches_email_case_insensitively(fake_session):
    owner = await auth.create_owner(
        fake_session, email="owner@example.com", name="Owner", password="Secret123"
    )

    user = await auth.authenticate(fake_session, email="OWNER@example.com ", password="Secret123")

    assert user is owner


async def test_authenticate_rejects_wrong_password(fake_session):
    await auth.create_owner(
        fake_session, email="owner@example.com", name="Owner", password="Secret123"
    )

    with pytest.raises(InvalidCredentialsError, match="invalid email or password"):
        await auth.authenticate(fake_session, email="owner@example.com", password="wrong")


async def test_authenticate_rejects_unknown_email(fake_session):
    with pytest.raises(InvalidCredentialsError):
        await auth.authenticate(fake_session, email="nobody@example.com", password="Secret123")


async def test_get_user_returns_none_for_unknown_id(fake_session):
    owner = await auth.create_owner(
        fake_session, email="owner@example.com", name="Owner", password="Secret123"
    )

    found = await auth.get_user(fake_session, owner.id)
    missing = await auth.get_user(fake_session, owner.id.__class__(int=0))

    assert found is owner
    assert missing is None
