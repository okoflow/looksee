import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

OPTIONAL_SETTINGS = (
    "MEDIAMTX_RTSP_URL",
    "MTX_MEDIA_USER",
    "MTX_MEDIA_PASSWORD",
    "RTSP_TRANSPORT",
    "MODELS_DIR",
    "FIRST_FRAME_TIMEOUT_SECONDS",
    "LAST_FRAME_TTL_SECONDS",
)


@pytest.fixture
def config(monkeypatch):
    for name in OPTIONAL_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    return importlib.import_module("inference.config")


def test_module_exposes_a_settings_instance(config):
    assert isinstance(config.settings, config.Settings)


def test_defaults_target_compose_services(config):
    settings = config.Settings(_env_file=None)

    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.mediamtx_rtsp_url == "rtsp://mediamtx:8554"
    assert settings.mtx_media_user == "media"
    assert settings.mtx_media_password == ""
    assert settings.rtsp_transport == "tcp"
    assert settings.models_dir == Path("models")
    assert settings.first_frame_timeout_seconds == 30.0
    assert settings.last_frame_ttl_seconds == 10


def test_requires_redis_url(config, monkeypatch):
    monkeypatch.delenv("REDIS_URL")

    with pytest.raises(ValidationError, match=r"redis_url\s+Field required"):
        config.Settings(_env_file=None)


def test_environment_overrides_defaults(config, monkeypatch):
    monkeypatch.setenv("MEDIAMTX_RTSP_URL", "rtsp://cams.local:8554")
    monkeypatch.setenv("MTX_MEDIA_USER", "viewer")
    monkeypatch.setenv("MTX_MEDIA_PASSWORD", "secret")
    monkeypatch.setenv("RTSP_TRANSPORT", "udp")
    monkeypatch.setenv("MODELS_DIR", "/srv/models")
    monkeypatch.setenv("FIRST_FRAME_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("LAST_FRAME_TTL_SECONDS", "3")

    settings = config.Settings(_env_file=None)

    assert settings.mediamtx_rtsp_url == "rtsp://cams.local:8554"
    assert settings.mtx_media_user == "viewer"
    assert settings.mtx_media_password == "secret"
    assert settings.rtsp_transport == "udp"
    assert settings.models_dir == Path("/srv/models")
    assert settings.first_frame_timeout_seconds == 2.5
    assert settings.last_frame_ttl_seconds == 3


def test_rejects_unknown_rtsp_transport(config, monkeypatch):
    monkeypatch.setenv("RTSP_TRANSPORT", "http")

    with pytest.raises(ValidationError, match="rtsp_transport"):
        config.Settings(_env_file=None)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("FIRST_FRAME_TIMEOUT_SECONDS", "0"),
        ("LAST_FRAME_TTL_SECONDS", "0"),
        ("LAST_FRAME_TTL_SECONDS", "-1"),
    ],
)
def test_rejects_non_positive_durations(config, monkeypatch, name, value):
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError, match="greater_than"):
        config.Settings(_env_file=None)


def test_reads_dotenv_and_ignores_foreign_keys(config, monkeypatch, tmp_path):
    monkeypatch.delenv("REDIS_URL")
    env_file = tmp_path / ".env"
    env_file.write_text("REDIS_URL=redis://from-file:6379/1\nDATABASE_URL=postgres://db\n")

    settings = config.Settings(_env_file=env_file)

    assert settings.redis_url == "redis://from-file:6379/1"


def test_environment_wins_over_dotenv(config, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("REDIS_URL=redis://from-file:6379/1\n")

    settings = config.Settings(_env_file=env_file)

    assert settings.redis_url == "redis://localhost:6379/0"
