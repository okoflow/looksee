from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.persistence.models import Camera, User
from api.domain.enums import CameraSource


class SqlAlchemyMediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def camera_source(self, camera_id: UUID) -> CameraSource | None:
        camera = await self._session.get(Camera, camera_id)

        return camera.source_type if camera is not None else None

    async def user_exists(self, user_id: UUID) -> bool:
        return await self._session.get(User, user_id) is not None
