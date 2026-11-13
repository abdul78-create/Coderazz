"""Pydantic schemas for the Human Annotation Queue."""

import uuid
from datetime import datetime
from typing import List, Optional

from backend.app.models.annotation import AnnotationTaskStatus
from pydantic import BaseModel, ConfigDict, Field


class AnnotationTaskResponse(BaseModel):
    """Payload representing an annotation review task."""

    id: uuid.UUID
    submission_id: uuid.UUID
    diagnosis_id: Optional[uuid.UUID] = None
    status: AnnotationTaskStatus
    assigned_annotator_id: Optional[uuid.UUID] = None
    original_misconception_code: str
    original_confidence: float
    trigger_reason: str
    resolved_misconception_code: Optional[str] = None
    annotator_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Contextual fields
    student_id: Optional[uuid.UUID] = None
    student_name: Optional[str] = None
    problem_id: Optional[uuid.UUID] = None
    problem_title: Optional[str] = None
    submission_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnnotationResolveRequest(BaseModel):
    """Payload for submitting a ground-truth taxonomy override."""

    resolved_misconception_code: str = Field(
        ...,
        min_length=2,
        max_length=16,
        description="Authoritative misconception code from taxonomy (e.g., A1, D4)",
    )
    annotator_notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Justification / diagnostic explanation from the human expert",
    )


class AnnotationQueueResponse(BaseModel):
    """Queue of review tasks awaiting human verification."""

    total_pending: int
    tasks: List[AnnotationTaskResponse]
