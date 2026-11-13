"""Submission database models for CodeRazz."""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from backend.app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.app.models.hint import HintRequest
    from backend.app.models.misconception import Diagnosis
    from backend.app.models.problem import Problem
    from backend.app.models.user import User


class SubmissionVerdict(str, enum.Enum):
    """Execution outcome verdicts."""

    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    SANDBOX_ERROR = "SANDBOX_ERROR"
    PENDING = "PENDING"


class SubmissionStatus(str, enum.Enum):
    """Submission lifecycle states."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Submission(Base):
    """User code submission record."""

    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        sa.String(32),
        default="python",
        nullable=False,
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        sa.Enum(SubmissionStatus, name="submission_status_enum"),
        default=SubmissionStatus.COMPLETED,
        nullable=False,
        index=True,
    )
    verdict: Mapped[SubmissionVerdict] = mapped_column(
        sa.Enum(SubmissionVerdict, name="submission_verdict_enum"),
        default=SubmissionVerdict.PENDING,
        nullable=False,
        index=True,
    )
    runtime_ms: Mapped[Optional[int]] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    memory_kb: Mapped[Optional[int]] = mapped_column(
        sa.Integer,
        nullable=True,
    )
    test_cases_passed: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        nullable=False,
    )
    total_test_cases: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        nullable=False,
    )
    stdout: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )
    stderr: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="submissions",
    )
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="submissions",
    )
    diagnoses: Mapped[list["Diagnosis"]] = relationship(
        "Diagnosis",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    hint_requests: Mapped[list["HintRequest"]] = relationship(
        "HintRequest",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
