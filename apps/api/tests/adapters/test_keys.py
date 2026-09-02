"""Process secret resolution and HKDF-derived subsystem keys."""

import pytest
from cryptography.fernet import InvalidToken

from api.adapters.security import keys
from api.config import settings


def clear_caches():
    keys._process_secret.cache_clear()
    keys.session_signing_key.cache_clear()
    keys.credentials_fernet.cache_clear()


@pytest.fixture
def secret_file(monkeypatch, tmp_path):
    path = tmp_path / "state" / "secret.key"
    monkeypatch.setattr(settings, "secret_key", None)
    monkeypatch.setattr(settings, "secret_key_file", path)
    clear_caches()

    return path


def test_missing_secret_is_generated_and_persisted_privately(secret_file):
    secret = keys._process_secret()

    assert secret_file.read_bytes() == secret
    assert len(secret) >= 48
    assert oct(secret_file.stat().st_mode & 0o777) == "0o600"


def test_persisted_secret_is_reused(secret_file):
    secret_file.parent.mkdir()
    secret_file.write_bytes(b"  stored-secret\n")

    assert keys._process_secret() == b"stored-secret"


def test_blank_secret_file_is_regenerated(secret_file):
    secret_file.parent.mkdir()
    secret_file.write_bytes(b"\n  \n")

    secret = keys._process_secret()

    assert secret.strip() == secret
    assert secret_file.read_bytes() == secret


def test_configured_secret_wins_over_the_file(secret_file, monkeypatch):
    secret_file.parent.mkdir()
    secret_file.write_bytes(b"file-secret")
    monkeypatch.setattr(settings, "secret_key", "env-secret")

    assert keys._process_secret() == b"env-secret"
    assert secret_file.read_bytes() == b"file-secret"


def test_derived_keys_are_deterministic_per_secret(monkeypatch):
    first = keys.session_signing_key()
    clear_caches()
    again = keys.session_signing_key()
    monkeypatch.setattr(settings, "secret_key", "another-secret")
    clear_caches()

    other = keys.session_signing_key()

    assert len(first) == 32
    assert first == again
    assert other != first


def test_subsystem_keys_are_domain_separated():
    assert keys._derive(b"looksee.sessions") != keys._derive(b"looksee.credentials")


def test_credentials_fernet_round_trips_only_under_the_same_secret(monkeypatch):
    token = keys.credentials_fernet().encrypt(b"payload")
    monkeypatch.setattr(settings, "secret_key", "rotated")
    clear_caches()

    with pytest.raises(InvalidToken):
        keys.credentials_fernet().decrypt(token)

    monkeypatch.setattr(settings, "secret_key", "unit-test-secret-key")
    clear_caches()
    assert keys.credentials_fernet().decrypt(token) == b"payload"
