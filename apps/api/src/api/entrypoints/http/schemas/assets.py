"""Asset store HTTP response bodies."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    size: int
    etag: str
    last_modified: datetime
