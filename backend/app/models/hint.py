"""Hint tracking and progression database models."""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from backend.app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.app.models.misconception import Diagnosis
    from backend.app.models.problem import Problem
    from backend.app.models.submission import Submission
    from backend.app.models.user import User


class HintTier(int, enum.Enum):
    """The 5 progressive pedagogical hint levels."""

    LEVEL_1_NUDGE = 1
    LEVEL_2_CONCEPTUAL = 2
    LEVEL_3_COUNTER_EXAMPLE = 3
    LEVEL_4_WORKED_ANALOGUE = 4
    LEVEL_5_TARGETED_POINTER = 5


class HintRequest(Base):
    """State record for a progressively unlocked pedagogical hint."""

    __tablename__ = "hint_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    diagnosis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("diagnoses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    hint_level: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        index=True,
    )
    hint_title: Mapped[str] = mapped_column(
        sa.String(128),
        nullable=False,
    )
    hint_content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    penalty_score: Mapped[float] = mapped_column(
        sa.Float,
        default=0.0,
        nullable=False,
    )
    leak_check_passed: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    submission: Mapped["Submission"] = relationship(
        "Submission",
        back_populates="hint_requests",
    )
    diagnosis: Mapped[Optional["Diagnosis"]] = relationship(
        "Diagnosis",
        back_populates="hint_requests",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="hint_requests",
    )
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="hint_requests",
    )
