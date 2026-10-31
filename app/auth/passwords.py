"""Password rules (R-AUTH-03) and argon2id hashing."""

from __future__ import annotations

import string

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# argon2id is the PasswordHasher default type; memory/time are explicit so the
# cost does not silently change between environments.
_hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)

MIN_LENGTH = 9  # "more than 8 characters" -> 9 or more
_SPECIAL = set(string.punctuation)


def validate_password(password: str) -> list[str]:
    """Return a list of human-readable rule violations (empty means valid)."""
    errors: list[str] = []
    if len(password or "") <= 8:
        errors.append("Password must be more than 8 characters long.")
    if not any(ch.isupper() for ch in password or ""):
        errors.append("Password must contain an uppercase letter.")
    if not any(ch.islower() for ch in password or ""):
        errors.append("Password must contain a lowercase letter.")
    if not any(ch in _SPECIAL for ch in password or ""):
        errors.append("Password must contain a special character.")
    return errors


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
