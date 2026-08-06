"""Edition entitlements HTTP entrypoint."""

from fastapi import APIRouter, Depends

from api.entrypoints.http.dependencies import EntitlementsDep, get_current_user
from api.entrypoints.http.schemas.entitlements import EntitlementsRead

router = APIRouter(
    prefix="/entitlements",
    tags=["entitlements"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
def read_entitlements(entitlements: EntitlementsDep) -> EntitlementsRead:
    """Expose the edition and licensed features so clients can lock paid nodes."""

    return EntitlementsRead(
        edition=entitlements.edition,
        features=sorted(entitlements.features),
    )
