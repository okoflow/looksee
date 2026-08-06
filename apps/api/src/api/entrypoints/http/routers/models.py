"""Model catalog HTTP entrypoint."""

from fastapi import APIRouter, Depends

from api.domain.models import ModelDescriptor
from api.entrypoints.http.dependencies import ModelCatalogDep, get_current_user

router = APIRouter(
    prefix="/models",
    tags=["models"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
def list_models(catalog: ModelCatalogDep) -> list[ModelDescriptor]:
    """Return the currently deployable model assets in deterministic order."""

    return list(catalog.list())
