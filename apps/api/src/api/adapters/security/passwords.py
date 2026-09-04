"""Argon2 password hashing behind a stable two-function surface."""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

_hasher = PasswordHash.recommended()
_DUMMY_HASH = _hasher.hash("looksee-placeholder-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password, password_hash)
    except (UnknownHashError, ValueError):
        return False


class Argon2Passwords:
    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, password: str, password_hash: str | None) -> bool:
        valid = verify_password(password, password_hash or _DUMMY_HASH)

        return password_hash is not None and valid
