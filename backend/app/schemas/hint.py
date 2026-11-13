"""Pydantic schemas for Hint Ladder requests and responses."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HintUnlockRequest(BaseModel):
    """Optional payload when requesting a hint unlock."""

    desired_level: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description=(
            "Next sequential hint level to unlock (1..5). "
            "If omitted, the next level is unlocked."
        ),
    )


class HintResponse(BaseModel):
    """Pedagogical hint response payload."""

    id: uuid.UUID
    submission_id: uuid.UUID
    user_id: uuid.UUID
    problem_id: uuid.UUID
    diagnosis_id: Optional[uuid.UUID] = None
    hint_level: int
    hint_tier_name: str
    hint_title: str
    hint_content: str
    penalty_score: float
    leak_check_passed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HintListResponse(BaseModel):
    """Collection of unlocked hints for a submission."""

    submission_id: uuid.UUID
    total_penalty: float
    max_unlocked_level: int
    hints: List[HintResponse]
