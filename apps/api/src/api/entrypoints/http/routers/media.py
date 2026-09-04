from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from api.application.media import MediaAction
from api.entrypoints.http.dependencies import CurrentUserDep, MediaAccessDep

router = APIRouter(tags=["media"])


class MediaAccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: MediaAction


class MediaAccessRead(BaseModel):
    token: str


class MediaAuthenticationRequest(BaseModel):
    action: str = Field(max_length=32)
    path: str = Field(default="", max_length=256)
    token: str = Field(default="", max_length=4096)
    user: str = Field(default="", max_length=256)
    password: str = Field(default="", max_length=512)
    ip: str = Field(default="", max_length=64)
    protocol: str = Field(default="", max_length=32)


@router.post("/cameras/{camera_id}/media-access")
async def issue_media_access(
    camera_id: UUID,
    payload: MediaAccessRequest,
    user: CurrentUserDep,
    access: MediaAccessDep,
    response: Response,
) -> MediaAccessRead:
    response.headers["Cache-Control"] = "no-store"

    return MediaAccessRead(token=await access.issue(user.id, camera_id, payload.action))


@router.post("/internal/media/auth", status_code=status.HTTP_204_NO_CONTENT)
async def authenticate_media(payload: MediaAuthenticationRequest, access: MediaAccessDep) -> None:
    if not await access.authorize(**payload.model_dump()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="access denied")
