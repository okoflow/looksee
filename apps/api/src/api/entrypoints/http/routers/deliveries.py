from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.application.deliveries import DeliveryHistory, DeliveryRecord, DeliveryStatus
from api.application.errors import ResourceConflictError
from api.entrypoints.http.dependencies import get_current_user, get_delivery_history

router = APIRouter(
    prefix="/deliveries", tags=["deliveries"], dependencies=[Depends(get_current_user)]
)
HistoryDep = Annotated[DeliveryHistory, Depends(get_delivery_history)]


@router.get("")
async def list_deliveries(
    history: HistoryDep,
    status: DeliveryStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[DeliveryRecord]:
    return await history.recent(status, limit)


@router.post("/{delivery_id}/retry", status_code=204)
async def retry_delivery(delivery_id: UUID, history: HistoryDep) -> None:
    if not await history.retry(delivery_id):
        raise ResourceConflictError("only existing failed deliveries can be retried")
