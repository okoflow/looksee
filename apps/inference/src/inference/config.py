"""Inference service configuration from the environment."""

from pathlib import Path
from typing import Annotated, Literal

from dotenv import find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=find_dotenv(), extra="ignore")

    redis_url: str
    mediamtx_rtsp_url: str = "rtsp://mediamtx:8554"
    mtx_media_user: str = "media"
    mtx_media_password: str = ""
    rtsp_transport: Literal["tcp", "udp"] = "tcp"
    models_dir: Path = Path("./models")
    first_frame_timeout_seconds: Annotated[float, Field(gt=0)] = 30.0
    last_frame_ttl_seconds: Annotated[int, Field(gt=0)] = 10


settings = Settings()
