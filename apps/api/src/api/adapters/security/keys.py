"""Process secret key and the HKDF-derived subsystem keys.

SECRET_KEY wins when set; otherwise the secret is generated once and persisted
to SECRET_KEY_FILE, so a fresh install needs no configuration.
"""

import base64
import fcntl
import os
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
    path.parent.mkdir(parents=True, exist_ok=True)

    # All readers lock the same file, including during concurrent first boot.
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "r+b") as secret_file:
        fcntl.flock(secret_file, fcntl.LOCK_EX)
        os.fchmod(secret_file.fileno(), 0o600)
        stored = secret_file.read().strip()
        if stored:
            return stored

        generated = secrets.token_urlsafe(48).encode()
        secret_file.seek(0)
        secret_file.write(generated)
        secret_file.truncate()
        secret_file.flush()
        os.fsync(secret_file.fileno())

        return generated


def derive_key(context: bytes) -> bytes:
    kdf = HKDF(algorithm=SHA256(), length=_KEY_LENGTH, salt=None, info=context)

    return kdf.derive(_process_secret())


@cache
def session_signing_key() -> bytes:
    return derive_key(b"looksee.sessions")


@cache
def credentials_fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(derive_key(b"looksee.credentials")))
