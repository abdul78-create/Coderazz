"""Pydantic schemas for Class Groups and Student Enrollments."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ClassGroupCreate(BaseModel):
    """Payload to create a new class group (Teacher only)."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=128,
        description="Name of the class (e.g., Intro to Python - Fall 2026)",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional syllabus or description for the class cohort",
    )


class ClassGroupResponse(BaseModel):
    """Class group details including join code."""

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    join_code: str
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    is_active: bool
    student_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClassJoinRequest(BaseModel):
    """Payload for a student joining a class via join code."""

    join_code: str = Field(
        ...,
        min_length=4,
        max_length=16,
        description="Alphanumeric class join code",
    )


class EnrollmentResponse(BaseModel):
    """Enrollment confirmation record."""

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    teacher_name: str
    student_id: uuid.UUID
    student_name: str
    student_email: str
    enrolled_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RosterStudentItem(BaseModel):
    """Student profile inside a class roster."""

    student_id: uuid.UUID
    full_name: str
    email: str
    enrolled_at: datetime
    submissions_count: int = 0
    total_hints_unlocked: int = 0
    total_penalty: float = 0.0


class ClassRosterResponse(BaseModel):
    """Full class roster with enrolled student profiles."""

    class_group: ClassGroupResponse
    students: List[RosterStudentItem]
