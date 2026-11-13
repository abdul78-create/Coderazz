"""Class roster and enrollment database models."""

import secrets
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy as sa
from backend.app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.app.models.user import User


def generate_join_code(length: int = 6) -> str:
    """Generate an unambiguous uppercase alphanumeric join code for student enrollment."""
    # Exclude easily confused characters (0/O, 1/I/L)
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(chars) for _ in range(length))


class ClassGroup(Base):
    """A classroom / cohort managed by a teacher with a unique join code."""

    __tablename__ = "class_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        sa.String(128),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )
    join_code: Mapped[str] = mapped_column(
        sa.String(16),
        unique=True,
        index=True,
        nullable=False,
        default=generate_join_code,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
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
    teacher: Mapped["User"] = relationship(
        "User",
        back_populates="taught_classes",
    )
    enrollments: Mapped[List["ClassEnrollment"]] = relationship(
        "ClassEnrollment",
        back_populates="class_group",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ClassGroup(name='{self.name}', join_code='{self.join_code}')>"


class ClassEnrollment(Base):
    """Association record representing a student's enrollment in a class group."""

    __tablename__ = "class_enrollments"
    __table_args__ = (
        sa.UniqueConstraint("class_id", "student_id", name="uq_class_student_enrollment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("class_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    class_group: Mapped["ClassGroup"] = relationship(
        "ClassGroup",
        back_populates="enrollments",
    )
    student: Mapped["User"] = relationship(
        "User",
        back_populates="class_enrollments",
    )

    def __repr__(self) -> str:
        return f"<ClassEnrollment(class_id='{self.class_id}', student_id='{self.student_id}')>"
