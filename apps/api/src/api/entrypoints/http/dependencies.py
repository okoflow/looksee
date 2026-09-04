"""FastAPI dependency aliases at the transport boundary."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.filesystem.model_catalog import ModelCatalog, model_catalog
from api.adapters.persistence.accounts import SqlAlchemyAccounts
from api.adapters.persistence.db import get_session, session_factory
from api.adapters.persistence.deliveries import PostgresDeliveryQueue
from api.adapters.persistence.media import SqlAlchemyMediaRepository
from api.adapters.persistence.models import User
from api.adapters.redis.rate_limits import RedisRateLimiter
from api.adapters.security import decode_session_token
from api.adapters.security.media import JwtMediaTokens
from api.adapters.security.passwords import Argon2Passwords
from api.application.auth import AccountRepository, Passwords, get_user
from api.application.deliveries import DeliveryHistory
from api.application.entitlements import Entitlements, resolve_entitlements
from api.application.media import MediaAccess
from api.application.rate_limits import RateLimiter
from api.config import settings

SESSION_COOKIE = "looksee_session"
_rate_limit_redis = Redis.from_url(settings.redis_url, socket_timeout=2)


def get_rate_limiter() -> RateLimiter:
    return RedisRateLimiter(_rate_limit_redis)


def get_delivery_history() -> DeliveryHistory:
    return PostgresDeliveryQueue(session_factory)


async def close_rate_limiter() -> None:
    await _rate_limit_redis.aclose()


async def require_auth_capacity(
    request: Request,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    client_ip = request.client.host if request.client is not None else "unknown"
    try:
        per_client = await limiter.allow(f"auth:{client_ip}", limit=20, window_seconds=60)
        global_capacity = await limiter.allow("auth:all", limit=100, window_seconds=60)
    except RedisError:
        raise HTTPException(
            status_code=503, detail="authentication temporarily unavailable"
        ) from None

    if not per_client or not global_capacity:
        raise HTTPException(
            status_code=429, detail="too many sign-in attempts", headers={"Retry-After": "60"}
        )


def get_model_catalog() -> ModelCatalog:
    return model_catalog


def get_entitlements() -> Entitlements:
    return resolve_entitlements(settings.license_key)


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_accounts(session: SessionDep) -> AccountRepository:
    return SqlAlchemyAccounts(session)


def get_passwords() -> Passwords:
    return Argon2Passwords()


AccountsDep = Annotated[AccountRepository, Depends(get_accounts)]
PasswordsDep = Annotated[Passwords, Depends(get_passwords)]


def get_media_access(session: SessionDep) -> MediaAccess:
    return MediaAccess(
        SqlAlchemyMediaRepository(session),
        JwtMediaTokens(),
        service_user=settings.mtx_media_user,
        service_password=settings.mtx_media_password,
    )


async def get_current_user(request: Request, accounts: AccountsDep) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    user_id = decode_session_token(token) if token is not None else None
    user = await get_user(accounts, user_id) if user_id is not None else None

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )

    return user


ModelCatalogDep = Annotated[ModelCatalog, Depends(get_model_catalog)]
EntitlementsDep = Annotated[Entitlements, Depends(get_entitlements)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
MediaAccessDep = Annotated[MediaAccess, Depends(get_media_access)]
