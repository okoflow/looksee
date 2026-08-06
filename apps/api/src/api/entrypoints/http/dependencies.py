"""FastAPI dependency aliases at the transport boundary."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.filesystem.model_catalog import ModelCatalog, model_catalog
from api.adapters.persistence.db import get_session
from api.adapters.persistence.models import User
from api.adapters.security import decode_session_token
from api.application.auth import get_user
from api.application.entitlements import Entitlements, resolve_entitlements
from api.config import settings

SESSION_COOKIE = "looksee_session"


def get_model_catalog() -> ModelCatalog:
    return model_catalog


def get_entitlements() -> Entitlements:
    return resolve_entitlements(settings.license_key)


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(request: Request, session: SessionDep) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    user_id = decode_session_token(token) if token is not None else None
    user = await get_user(session, user_id) if user_id is not None else None

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )

    return user


ModelCatalogDep = Annotated[ModelCatalog, Depends(get_model_catalog)]
EntitlementsDep = Annotated[Entitlements, Depends(get_entitlements)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
