"""Human-in-the-Loop Annotation Queue database models."""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from backend.app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.app.models.misconception import Diagnosis, MisconceptionTaxonomy
    from backend.app.models.submission import Submission
    from backend.app.models.user import User


class AnnotationTaskStatus(str, enum.Enum):
    """Lifecycle status of an annotation task."""

    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AnnotationTask(Base):
    """A human review task spawned when diagnostic confidence is low (<0.50) or novel (S2)."""

    __tablename__ = "annotation_tasks"

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
    status: Mapped[AnnotationTaskStatus] = mapped_column(
        sa.Enum(AnnotationTaskStatus, name="annotation_task_status_enum", native_enum=True),
        default=AnnotationTaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_annotator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_misconception_code: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        index=True,
    )
    original_confidence: Mapped[float] = mapped_column(
        sa.Float,
        nullable=False,
    )
    trigger_reason: Mapped[str] = mapped_column(
        sa.String(128),
        nullable=False,
    )
    resolved_misconception_code: Mapped[Optional[str]] = mapped_column(
        sa.String(16),
        sa.ForeignKey("misconception_taxonomy.code", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    annotator_notes: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    submission: Mapped["Submission"] = relationship(
        "Submission",
        back_populates="annotation_tasks",
    )
    diagnosis: Mapped[Optional["Diagnosis"]] = relationship(
        "Diagnosis",
        back_populates="annotation_tasks",
    )
    assigned_annotator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_annotator_id],
    )
    resolved_taxonomy: Mapped[Optional["MisconceptionTaxonomy"]] = relationship(
        "MisconceptionTaxonomy",
        foreign_keys=[resolved_misconception_code],
    )

    def __repr__(self) -> str:
        return f"<AnnotationTask(id={self.id}, status={self.status})>"
