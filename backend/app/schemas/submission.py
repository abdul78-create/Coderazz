"""Pydantic schemas for code execution and submission endpoints."""

import uuid
from datetime import datetime
from typing import List, Optional

from backend.app.models.submission import SubmissionStatus, SubmissionVerdict
from backend.app.services.sandbox import TestCaseExecutionResult
from pydantic import BaseModel, ConfigDict, Field


class CodeRunRequest(BaseModel):
    """Payload to test code interactively in the workspace without saving to history."""

    code: str = Field(..., min_length=1, max_length=65536, description="Python code to execute")
    problem_id: Optional[uuid.UUID] = Field(
        None, description="Problem ID to load sample test cases"
    )
    custom_input: Optional[str] = Field(None, description="Optional custom stdin input")


class CodeRunResponse(BaseModel):
    """Result of an interactive code run."""

    verdict: SubmissionVerdict
    stdout: str
    stderr: str
    runtime_ms: int
    memory_kb: int
    test_cases_passed: int
    total_test_cases: int
    error_message: Optional[str] = None
    test_cases: List[TestCaseExecutionResult] = []


class SubmissionCreateRequest(BaseModel):
    """Payload to submit code for final grading against all hidden test cases."""

    problem_id: uuid.UUID = Field(..., description="Target problem ID")
    code: str = Field(..., min_length=1, max_length=65536, description="Python code submission")
    language: str = Field(default="python", max_length=32)


class SubmissionResponse(BaseModel):
    """Full submission result record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    problem_id: uuid.UUID
    user_id: uuid.UUID
    code: str
    language: str
    status: SubmissionStatus
    verdict: SubmissionVerdict
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    test_cases_passed: int
    total_test_cases: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    problem_title: Optional[str] = None
    problem_slug: Optional[str] = None


class SubmissionListItemResponse(BaseModel):
    """Summary item for submission history tables."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    problem_id: uuid.UUID
    problem_title: str
    problem_slug: str
    verdict: SubmissionVerdict
    status: SubmissionStatus
    runtime_ms: Optional[int] = None
    test_cases_passed: int
    total_test_cases: int
    created_at: datetime
