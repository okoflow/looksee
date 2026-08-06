from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import find_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(),
        extra="ignore",
    )

    app_name: str = "LookSee API"

    # LookSee Enterprise license key; unset runs the community edition.
    license_key: str | None = None

    database_url: str = "postgresql+asyncpg://looksee:looksee@localhost:5432/looksee"
    redis_url: str = "redis://localhost:6379/0"

    consumer_group: str = "api-workers"

    mediamtx_api_url: str = "http://localhost:9997"
    # S3-compatible asset store for "file" camera sources, built for Cloudflare R2:
    # endpoint https://<account_id>.r2.cloudflarestorage.com, region "auto".
    # Endpoint or bucket left empty = asset store (and the /assets API) disabled.
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket: str = ""
    s3_region: str = "auto"
    s3_prefix: str = ""
    # Writable cache where assets are downloaded for playback; the same volume is
    # mounted read-only into the mediamtx container at media_mount_dir.
    media_cache_dir: str = "./data/media-cache"
    # Where the media volume is mounted inside the mediamtx container; file
    # sources resolve against it in the ffmpeg publish command.
    media_mount_dir: str = "/media"
    models_dir: Path = Path("./models")
    event_cooldown_seconds: float = Field(default=2.0, ge=0.0, allow_inf_nan=False)
    event_timezone: ZoneInfo = ZoneInfo("UTC")

    reconcile_interval_seconds: float = Field(default=30.0, gt=0.0, allow_inf_nan=False)

    snapshots_dir: Path = Path("./data/snapshots")

    # Root secret for session signing and credential encryption. Unset, a
    # secret is generated once and persisted to secret_key_file.
    secret_key: str | None = None
    secret_key_file: Path = Path("./data/secret.key")
    # Session cookies stay SameSite=Lax; enable Secure behind HTTPS.
    auth_cookie_secure: bool = False

    cors_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @field_validator(
        "license_key",
        "secret_key",
        mode="before",
    )
    @classmethod
    def blank_optional_to_none(cls, value: object) -> object:
        """Treat blank env values as unset so integrations key off `is None` only."""
        if isinstance(value, str) and not value.strip():
            return None

        return value


settings = Settings()
