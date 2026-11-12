"""Pydantic schemas for problem and test case management."""

import uuid
from datetime import datetime
from typing import List, Optional

from backend.app.models.problem import ProblemDifficulty
from pydantic import BaseModel, ConfigDict, Field


class TestCasePublicResponse(BaseModel):
    """Public sample test case data visible to students."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_index: int
    input_data: str
    expected_output: str
    explanation: Optional[str] = None


class TestCaseAdminResponse(BaseModel):
    """Full test case specification visible only to teachers and administrators."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    problem_id: uuid.UUID
    order_index: int
    input_data: str
    expected_output: str
    is_hidden: bool
    explanation: Optional[str] = None
    created_at: datetime


class ProblemListItemResponse(BaseModel):
    """Summary item for the problems catalog listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    difficulty: ProblemDifficulty
    category: str
    order_index: int
    is_published: bool
    sample_cases_count: int = 0
    total_cases_count: int = 0


class ProblemDetailResponse(BaseModel):
    """Full problem details for the student coding workspace."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    description: str
    difficulty: ProblemDifficulty
    category: str
    starter_code: str
    time_limit_ms: int
    memory_limit_mb: int
    order_index: int
    sample_test_cases: List[TestCasePublicResponse] = []


class TestCaseCreateRequest(BaseModel):
    """Request payload to add a test case to a problem."""

    input_data: str = Field(..., description="Standard input text")
    expected_output: str = Field(..., description="Expected standard output text")
    is_hidden: bool = Field(default=False, description="Whether this is a secret evaluation case")
    explanation: Optional[str] = Field(None, description="Optional educational explanation")
    order_index: int = Field(default=0, description="Display / execution order")


class ProblemCreateRequest(BaseModel):
    """Request payload for teachers and admins to create a programming challenge."""

    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=10)
    difficulty: ProblemDifficulty = Field(default=ProblemDifficulty.EASY)
    category: str = Field(default="General", max_length=100)
    starter_code: str = Field(...)
    solution_template: Optional[str] = None
    time_limit_ms: int = Field(default=3000, ge=500, le=10000)
    memory_limit_mb: int = Field(default=128, ge=32, le=512)
    order_index: int = Field(default=0)
    test_cases: List[TestCaseCreateRequest] = []
