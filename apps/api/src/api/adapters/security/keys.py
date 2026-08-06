"""Process secret key and the HKDF-derived subsystem keys.

SECRET_KEY wins when set; otherwise the secret is generated once and persisted
to SECRET_KEY_FILE, so a fresh install needs no configuration.
"""

import base64
import secrets
from functools import cache

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from api.config import settings

_KEY_LENGTH = 32


@cache
def _process_secret() -> bytes:
    if settings.secret_key is not None:
        return settings.secret_key.encode()

    path = settings.secret_key_file
    if path.is_file():
        stored = path.read_bytes().strip()
        if stored:
            return stored

    generated = secrets.token_urlsafe(48).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    path.write_bytes(generated)

    return generated


def _derive(context: bytes) -> bytes:
    kdf = HKDF(algorithm=SHA256(), length=_KEY_LENGTH, salt=None, info=context)

    return kdf.derive(_process_secret())


@cache
def session_signing_key() -> bytes:
    return _derive(b"looksee.sessions")


@cache
def credentials_fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(_derive(b"looksee.credentials")))
