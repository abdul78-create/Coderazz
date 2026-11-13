"""Misconception taxonomy and diagnostic database models."""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

import sqlalchemy as sa
from backend.app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.app.models.submission import Submission


class DetectorType(str, enum.Enum):
    """Origin of a misconception diagnosis."""

    RULE_AST = "rule_ast"
    PROBE = "probe"
    ML_CLASSIFIER = "ml_classifier"
    FUSION = "fusion"
    HUMAN_OVERRIDE = "human_override"


class MisconceptionTaxonomy(Base):
    """Authoritative taxonomy definition of a programming misconception."""

    __tablename__ = "misconception_taxonomy"

    code: Mapped[str] = mapped_column(
        sa.String(16),
        primary_key=True,
    )
    category: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        sa.String(128),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    pedagogical_remedy: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        sa.String(16),
        default="MEDIUM",
        nullable=False,
    )
    is_meta: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    diagnoses: Mapped[list["Diagnosis"]] = relationship(
        "Diagnosis",
        back_populates="misconception",
        cascade="all, delete-orphan",
    )


class Diagnosis(Base):
    """Diagnostic outcome linking a submission to a detected misconception."""

    __tablename__ = "diagnoses"

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
    misconception_code: Mapped[str] = mapped_column(
        sa.String(16),
        sa.ForeignKey("misconception_taxonomy.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    confidence_score: Mapped[float] = mapped_column(
        sa.Float,
        default=1.0,
        nullable=False,
    )
    detector_type: Mapped[DetectorType] = mapped_column(
        sa.Enum(DetectorType, name="detector_type_enum"),
        default=DetectorType.RULE_AST,
        nullable=False,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    evidence_lines: Mapped[Optional[list[int]]] = mapped_column(
        sa.JSON,
        nullable=True,
    )
    explanation: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        sa.JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    submission: Mapped["Submission"] = relationship(
        "Submission",
        back_populates="diagnoses",
    )
    misconception: Mapped["MisconceptionTaxonomy"] = relationship(
        "MisconceptionTaxonomy",
        back_populates="diagnoses",
    )
