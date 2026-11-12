"""Unit tests for Argon2 password hashing and JWT security functions."""

from datetime import timedelta

import jwt
import pytest

from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hashing_and_verification():
    """Verify Argon2 hashes passwords with salt and verifies matches correctly."""
    plain = "SuperSecurePassword#2026"
    hashed = hash_password(plain)

    # Assert hash structure is Argon2id
    assert hashed.startswith("$argon2id$")
    assert hashed != plain

    # Successful verification
    assert verify_password(plain, hashed) is True

    # Incorrect password failure
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password("", hashed) is False


def test_password_hashes_are_unique_for_same_password():
    """Verify random salt generates different Argon2 hashes for identical plaintexts."""
    pwd = "IdenticalPassword!123"
    hash1 = hash_password(pwd)
    hash2 = hash_password(pwd)

    assert hash1 != hash2
    assert verify_password(pwd, hash1) is True
    assert verify_password(pwd, hash2) is True


def test_access_token_creation_and_decoding():
    """Verify JWT access tokens carry expected claims and decode properly."""
    sub = "user-1234-uuid"
    role = "student"
    token = create_access_token(subject=sub, role=role)

    payload = decode_access_token(token)
    assert payload["sub"] == sub
    assert payload["role"] == role
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_expired_token_rejection():
    """Verify expired JWT tokens raise ExpiredSignatureError."""
    sub = "user-expired-uuid"
    token = create_access_token(
        subject=sub,
        role="student",
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_rejection():
    """Verify tampered JWT tokens raise DecodeError or InvalidSignatureError."""
    token = create_access_token(subject="user-uuid", role="student")
    tampered = token[:-4] + "abcd"

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered)


def test_refresh_token_generation_and_hashing():
    """Verify refresh tokens are high-entropy and generate deterministic SHA-256 hashes."""
    raw1, hash1, exp1 = generate_refresh_token()
    raw2, hash2, exp2 = generate_refresh_token()

    assert raw1 != raw2
    assert hash1 != hash2
    assert len(hash1) == 64  # SHA-256 hex length
    assert hash_token(raw1) == hash1
    assert hash_token(raw2) == hash2
    assert exp1 > exp1 - timedelta(days=1)
    assert exp2 > exp2 - timedelta(days=1)

