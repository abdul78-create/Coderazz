"""Problem and TestCase database models for CodeRazz."""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy as sa
from backend.app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.app.models.submission import Submission


class ProblemDifficulty(str, enum.Enum):
    """Problem difficulty categories."""

    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Problem(Base):
    """Programming challenge definition."""

    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(
        sa.String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    difficulty: Mapped[ProblemDifficulty] = mapped_column(
        sa.Enum(ProblemDifficulty, name="problem_difficulty_enum"),
        default=ProblemDifficulty.EASY,
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        sa.String(100),
        default="General",
        nullable=False,
        index=True,
    )
    starter_code: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    solution_template: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )
    time_limit_ms: Mapped[int] = mapped_column(
        sa.Integer,
        default=3000,
        nullable=False,
    )
    memory_limit_mb: Mapped[int] = mapped_column(
        sa.Integer,
        default=128,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        nullable=False,
    )
    is_published: Mapped[bool] = mapped_column(
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
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="TestCase.order_index",
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="problem",
        cascade="all, delete-orphan",
    )


class TestCase(Base):
    """Test case specification for a programming problem."""

    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_data: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    expected_output: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    is_hidden: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    explanation: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )
    order_index: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="test_cases",
    )
