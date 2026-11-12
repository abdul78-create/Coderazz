"""Security utilities: Argon2 password hashing and PyJWT token management."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from backend.app.config import get_settings

# Initialize Argon2 password hasher with secure defaults
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash plaintext password using Argon2."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against an Argon2 hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def create_access_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
    extra_claims: Dict[str, Any] | None = None,
) -> str:
    """Generate signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
        "iss": settings.APP_NAME,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises jwt.PyJWTError on expiration, tamper, or invalid structure.
    """
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        issuer=settings.APP_NAME,
        options={"require": ["sub", "exp", "role"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Token is not an access token")
    return payload


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Generate a high-entropy refresh token string, its SHA-256 hash, and expiration timestamp."""
    settings = get_settings()
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return raw_token, token_hash, expires_at


def hash_token(token: str) -> str:
    """Compute deterministic SHA-256 hash of a token string for safe DB indexing."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

