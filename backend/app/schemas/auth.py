"""Pydantic schemas for authentication and authorization."""

import re
import uuid
from datetime import datetime

from backend.app.models.user import UserRole
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Strong account password")
    full_name: str = Field(..., min_length=2, max_length=100, description="User's display name")
    role: UserRole = Field(
        default=UserRole.STUDENT,
        description="Desired role. Public registration accepts 'student' or 'teacher' only.",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce password complexity (min 8 chars, at least one letter and one number)."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("role")
    @classmethod
    def validate_public_registration_role(cls, v: UserRole) -> UserRole:
        """Prevent privilege escalation: ADMIN and ANNOTATOR roles cannot be self-assigned."""
        if v in [UserRole.ADMIN, UserRole.ANNOTATOR]:
            raise ValueError(
                f"Privilege escalation prevented: Role '{v.value}' cannot be self-assigned. "
                "Contact a platform administrator."
            )
        return v


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserProfileResponse(BaseModel):
    """Public user profile data contract (never returns password hashes)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """Authentication token response payload."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserProfileResponse


class RefreshTokenRequest(BaseModel):
    """Payload to exchange a refresh token for a new access token."""

    refresh_token: str = Field(..., min_length=20, description="Valid refresh token string")


class RoleUpdateRequest(BaseModel):
    """Admin-only payload to update a user's role."""

    role: UserRole = Field(..., description="Target role to assign")


class MessageResponse(BaseModel):
    """Generic status response payload."""

    message: str
    status: str = "ok"

