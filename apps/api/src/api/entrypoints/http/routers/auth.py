"""Session auth entrypoints: first-run owner setup, login, logout, me."""

from fastapi import APIRouter, Depends, Response, status

from api.adapters.persistence.models import User
from api.adapters.security import SESSION_TTL, issue_session_token
from api.application import auth
from api.config import settings
from api.entrypoints.http.dependencies import (
    SESSION_COOKIE,
    AccountsDep,
    CurrentUserDep,
    PasswordsDep,
    require_auth_capacity,
)
from api.entrypoints.http.schemas.auth import (
    AuthStatusRead,
    LoginRequest,
    SetupRequest,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _attach_session(response: Response, user: User) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        issue_session_token(user.id),
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        path="/",
    )


@router.get("/status")
async def auth_status(accounts: AccountsDep) -> AuthStatusRead:
    return AuthStatusRead(requires_setup=await auth.requires_setup(accounts))


@router.post(
    "/setup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_auth_capacity)],
)
async def setup_owner(
    payload: SetupRequest,
    accounts: AccountsDep,
    passwords: PasswordsDep,
    response: Response,
) -> User:
    owner = await auth.create_owner(
        accounts,
        passwords,
        email=payload.email,
        name=payload.name,
        password=payload.password,
    )
    _attach_session(response, owner)

    return owner


@router.post("/login", response_model=UserRead, dependencies=[Depends(require_auth_capacity)])
async def login(
    payload: LoginRequest, accounts: AccountsDep, passwords: PasswordsDep, response: Response
) -> User:
    user = await auth.authenticate(
        accounts, passwords, email=payload.email, password=payload.password
    )
    _attach_session(response, user)

    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUserDep) -> User:
    return user
