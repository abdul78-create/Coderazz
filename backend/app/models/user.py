"""User model and role definitions."""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

import sqlalchemy as sa
from backend.app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.app.models.token import RefreshToken


class UserRole(str, enum.Enum):
    """Authoritative role definitions for CodeRazz RBAC."""
    STUDENT = "student"
    TEACHER = "teacher"
    ANNOTATOR = "annotator"
    ADMIN = "admin"


class User(Base):
    """User entity representing authenticated platform participants."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, name="user_role_enum", native_enum=True),
        default=UserRole.STUDENT,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(email={self.email}, role={self.role})>"

