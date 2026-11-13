"""Pydantic schemas for Class Analytics and Struggle Trends."""

import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class MisconceptionFrequencyItem(BaseModel):
    """Aggregate frequency stats for a specific detected misconception."""

    misconception_code: str
    misconception_name: str
    category: str
    severity: str
    count: int
    unique_students: int
    percentage: float

    model_config = ConfigDict(from_attributes=True)


class ClassMisconceptionAnalyticsResponse(BaseModel):
    """Class-wide misconception distribution."""

    class_id: uuid.UUID
    class_name: str
    problem_id: Optional[uuid.UUID] = None
    total_diagnoses: int
    total_students_diagnosed: int
    misconceptions: List[MisconceptionFrequencyItem]


class DailyStrugglePoint(BaseModel):
    """Daily time-series observation of class activity and struggle indicators."""

    date: str
    submissions_count: int
    unique_students_active: int
    hints_requested_count: int
    failing_submissions_count: int
    diagnoses_count: int


class ClassStruggleTrendsResponse(BaseModel):
    """Class-wide longitudinal struggle and activity time-series."""

    class_id: uuid.UUID
    class_name: str
    time_window_days: int
    total_submissions: int
    total_hints: int
    trend: List[DailyStrugglePoint]
