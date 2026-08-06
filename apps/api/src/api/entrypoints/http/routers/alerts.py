"""Alert HTTP entrypoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from api.adapters.persistence.models import Alert
from api.application import alerts
from api.domain.enums import AlertSeverity
from api.entrypoints.http.dependencies import SessionDep, get_current_user
from api.entrypoints.http.schemas.alerts import AlertRead

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    session: SessionDep,
    camera_id: UUID | None = None,
    workflow_id: UUID | None = None,
    severity: AlertSeverity | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[Alert]:
    return await alerts.list_alerts(
        session,
        camera_id=camera_id,
        workflow_id=workflow_id,
        severity=severity,
        limit=limit,
    )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    session: SessionDep,
) -> None:
    await alerts.delete_alert(session, alert_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_alerts(
    session: SessionDep,
    camera_id: UUID | None = None,
    workflow_id: UUID | None = None,
) -> None:
    await alerts.clear_alerts(
        session,
        camera_id=camera_id,
        workflow_id=workflow_id,
    )
