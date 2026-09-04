"""Camera-scoped media authorization."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Literal, Protocol
from uuid import UUID

from api.application.errors import InvalidCredentialsError, ResourceNotFoundError
from api.domain.enums import CameraSource

type MediaAction = Literal["read", "publish"]


@dataclass(frozen=True, slots=True)
class MediaGrant:
    user_id: UUID
    camera_id: UUID
    action: MediaAction


class MediaRepository(Protocol):
    async def camera_source(self, camera_id: UUID) -> CameraSource | None: ...

    async def user_exists(self, user_id: UUID) -> bool: ...


class MediaTokens(Protocol):
    def issue(self, grant: MediaGrant) -> str: ...

    def decode(self, token: str) -> MediaGrant | None: ...


class MediaAccess:
    def __init__(
        self,
        repository: MediaRepository,
        tokens: MediaTokens,
        *,
        service_user: str,
        service_password: str,
    ) -> None:
        self._repository = repository
        self._tokens = tokens
        self._service_user = service_user
        self._service_password = service_password

    async def issue(self, user_id: UUID, camera_id: UUID, action: MediaAction) -> str:
        source = await self._repository.camera_source(camera_id)
        if source is None:
            raise ResourceNotFoundError("camera not found")
        if action == "publish" and source != CameraSource.WEBRTC:
            raise InvalidCredentialsError("this camera does not accept browser publishers")

        return self._tokens.issue(MediaGrant(user_id, camera_id, action))

    async def authorize(
        self,
        *,
        action: str,
        path: str,
        token: str,
        user: str,
        password: str,
        ip: str,
        protocol: str,
    ) -> bool:
        service = (
            bool(self._service_password)
            and hmac.compare_digest(user.encode(), self._service_user.encode())
            and hmac.compare_digest(password.encode(), self._service_password.encode())
        )
        if action == "api":
            return service
        if action not in ("read", "publish"):
            return False

        try:
            camera_id = UUID(path)
        except ValueError:
            return False
        if path != str(camera_id):
            return False

        source = await self._repository.camera_source(camera_id)
        if source is None:
            return False
        if service and action == "read":
            return True
        if action == "publish" and source == CameraSource.FILE and protocol == "rtsp":
            try:
                return ip_address(ip).is_loopback
            except ValueError:
                return False
        if action == "publish" and source != CameraSource.WEBRTC:
            return False

        grant = self._tokens.decode(token)
        if grant is None or grant.camera_id != camera_id or grant.action != action:
            return False

        return await self._repository.user_exists(grant.user_id)
