from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from api.adapters.persistence.models import Camera, Workflow
from api.application.frame_processing import CameraFrameContext

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyFrameContexts:
    def __init__(self, sessions: Callable[[], AsyncSession]) -> None:
        self._sessions = sessions

    async def load(self, camera_id: UUID) -> CameraFrameContext | None:
        statement = (
            select(
                Camera.workflow_id,
                Camera.node_id,
                Camera.name,
                Camera.start_command,
                Workflow.enabled,
                Workflow.graph,
            )
            .join(Workflow, Workflow.id == Camera.workflow_id)
            .where(Camera.id == camera_id)
        )
        async with self._sessions() as session:
            row = (await session.execute(statement)).one_or_none()

        if row is None:
            return None

        return CameraFrameContext(
            workflow_id=row.workflow_id,
            node_id=row.node_id,
            name=row.name,
            start_command=row.start_command,
            enabled=row.enabled,
            graph=row.graph,
        )
