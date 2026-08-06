"""Alert query and deletion use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from api.adapters.persistence.models import Alert
from api.application.errors import ResourceNotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import ColumnElement
    from sqlalchemy.ext.asyncio import AsyncSession

    from api.domain.enums import AlertSeverity


def _scope_filters(camera_id: UUID | None, workflow_id: UUID | None) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if camera_id is not None:
        filters.append(Alert.camera_id == camera_id)
    if workflow_id is not None:
        filters.append(Alert.workflow_id == workflow_id)

    return filters


async def list_alerts(
    session: AsyncSession,
    *,
    camera_id: UUID | None,
    workflow_id: UUID | None,
    severity: AlertSeverity | None,
    limit: int,
) -> list[Alert]:
    statement = select(Alert).where(*_scope_filters(camera_id, workflow_id))
    if severity is not None:
        statement = statement.where(Alert.severity == severity)

    result = await session.execute(statement.order_by(Alert.created_at.desc()).limit(limit))

    return list(result.scalars().all())


async def delete_alert(session: AsyncSession, alert_id: UUID) -> None:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise ResourceNotFoundError("alert not found")

    await session.delete(alert)
    await session.commit()


async def clear_alerts(
    session: AsyncSession,
    *,
    camera_id: UUID | None,
    workflow_id: UUID | None,
) -> None:
    statement = delete(Alert).where(*_scope_filters(camera_id, workflow_id))

    await session.execute(statement)
    await session.commit()
