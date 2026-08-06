"""Asset store endpoints backing "file" camera sources."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from api.application import assets
from api.entrypoints.http.dependencies import get_current_user
from api.entrypoints.http.schemas.assets import AssetRead

router = APIRouter(
    prefix="/assets",
    tags=["assets"],
    dependencies=[Depends(get_current_user)],
)


def _store_unavailable(error: assets.AssetStoreNotConfiguredError) -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error))


@router.get("")
async def list_assets() -> list[AssetRead]:
    try:
        stored = await assets.list_assets()
    except assets.AssetStoreNotConfiguredError as error:
        raise _store_unavailable(error) from error

    return [AssetRead.model_validate(asset) for asset in stored]


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_asset(file: UploadFile) -> AssetRead:
    filename = file.filename if file.filename else "asset"
    content_type = file.content_type if file.content_type else "application/octet-stream"

    try:
        stored = await assets.upload_asset(filename, file.file, content_type)
    except assets.AssetStoreNotConfiguredError as error:
        raise _store_unavailable(error) from error

    return AssetRead.model_validate(stored)


@router.get("/{key:path}/content")
async def read_asset_content(key: str) -> FileResponse:
    """Serve the asset from the local playback cache; FileResponse handles range requests."""
    try:
        path, media_type = await assets.cached_asset_file(key)
    except assets.AssetStoreNotConfiguredError as error:
        raise _store_unavailable(error) from error
    except assets.AssetNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error

    return FileResponse(path, media_type=media_type)


@router.delete("/{key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(key: str) -> None:
    try:
        await assets.delete_asset(key)
    except assets.AssetStoreNotConfiguredError as error:
        raise _store_unavailable(error) from error
    except assets.AssetNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
