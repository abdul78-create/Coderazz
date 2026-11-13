"""Pedagogical Hint Ladder API endpoints."""

import uuid
from typing import Optional

from backend.app.core.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models.hint import HintRequest
from backend.app.models.misconception import MisconceptionTaxonomy
from backend.app.models.submission import Submission, SubmissionVerdict
from backend.app.models.user import User, UserRole
from backend.app.schemas.hint import HintListResponse, HintResponse, HintUnlockRequest
from backend.app.services.hint_ladder import TIER_NAMES, HintLadderService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(tags=["Pedagogical Hint Ladder"])
hint_service = HintLadderService()


@router.post(
    "/submissions/{submission_id}/hints",
    response_model=HintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Unlock the next progressive pedagogical hint",
)
async def unlock_next_hint(
    submission_id: uuid.UUID,
    body: Optional[HintUnlockRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HintResponse:
    """Progressively unlock the next pedagogical hint tier (Level 1..5).

    Enforces:
    - Ownership verification: students cannot request hints on others' submissions.
    - Strict sequential progression: cannot skip tiers (Level N+1 requires Level N).
    - Hard ceiling at Level 5.
    - SolutionLeakGuard validation preventing reference solution leakage.
    - Diagnostic alignment with primary detected misconception.
    """
    stmt = (
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.problem),
            selectinload(Submission.diagnoses),
            selectinload(Submission.hint_requests),
        )
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    # RBAC: students can only unlock hints on their own submissions
    if current_user.role == UserRole.STUDENT and submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to unlock hints for another student's submission.",
        )

    if submission.verdict == SubmissionVerdict.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This submission passed all test cases. No misconception was diagnosed.",
        )

    # Determine next sequential level
    existing_hints = sorted(submission.hint_requests, key=lambda h: h.hint_level)
    unlocked_levels = {h.hint_level for h in existing_hints}
    max_unlocked = max(unlocked_levels, default=0)
    next_level = max_unlocked + 1

    if next_level > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All 5 progressive hint levels have already been unlocked for this submission.",
        )

    # Verify sequential unlock if desired_level is explicitly requested
    if body and body.desired_level is not None:
        if body.desired_level != next_level:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Hints must be unlocked sequentially. Next tier is Level {next_level}, "
                    f"but Level {body.desired_level} was requested."
                ),
            )

    # Retrieve primary misconception diagnosis
    primary_diag = next((d for d in submission.diagnoses if d.is_primary), None)
    if not primary_diag and submission.diagnoses:
        primary_diag = submission.diagnoses[0]

    misconception_code = primary_diag.misconception_code if primary_diag else "A1"
    evidence_lines = primary_diag.evidence_lines if primary_diag else None

    # Fetch taxonomy remedy metadata
    tax_query = select(MisconceptionTaxonomy).where(
        MisconceptionTaxonomy.code == misconception_code
    )
    tax_res = await db.execute(tax_query)
    taxonomy = tax_res.scalar_one_or_none()
    taxonomy_name = taxonomy.name if taxonomy else misconception_code
    taxonomy_remedy = taxonomy.pedagogical_remedy if taxonomy else ""

    # Generate hint through the 5-Tier Hint Ladder
    problem = submission.problem
    reference_solution = problem.solution_template if problem else ""
    problem_title = problem.title if problem else ""

    generated = hint_service.generate_hint(
        hint_level=next_level,
        misconception_code=misconception_code,
        reference_solution=reference_solution or "",
        problem_title=problem_title,
        evidence_lines=evidence_lines,
        student_code=submission.code,
        taxonomy_remedy=taxonomy_remedy,
        taxonomy_name=taxonomy_name,
    )

    # Persist HintRequest
    hint_record = HintRequest(
        submission_id=submission.id,
        diagnosis_id=primary_diag.id if primary_diag else None,
        user_id=submission.user_id,
        problem_id=submission.problem_id,
        hint_level=next_level,
        hint_title=generated.hint_title,
        hint_content=generated.hint_content,
        penalty_score=generated.penalty_score,
        leak_check_passed=generated.leak_check_passed,
    )
    db.add(hint_record)
    await db.commit()
    await db.refresh(hint_record)

    return HintResponse(
        id=hint_record.id,
        submission_id=hint_record.submission_id,
        user_id=hint_record.user_id,
        problem_id=hint_record.problem_id,
        diagnosis_id=hint_record.diagnosis_id,
        hint_level=hint_record.hint_level,
        hint_tier_name=generated.hint_tier_name,
        hint_title=hint_record.hint_title,
        hint_content=hint_record.hint_content,
        penalty_score=hint_record.penalty_score,
        leak_check_passed=hint_record.leak_check_passed,
        created_at=hint_record.created_at,
    )


@router.get(
    "/submissions/{submission_id}/hints",
    response_model=HintListResponse,
    summary="Retrieve all unlocked hints for a submission",
)
async def get_unlocked_hints(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HintListResponse:
    """Retrieve all previously unlocked hints for a specific submission."""
    stmt = (
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.hint_requests))
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    # RBAC: students can only view hints for their own submissions
    if current_user.role == UserRole.STUDENT and submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view hints for another student's submission.",
        )

    sorted_hints = sorted(submission.hint_requests, key=lambda h: h.hint_level)
    hint_responses = [
        HintResponse(
            id=h.id,
            submission_id=h.submission_id,
            user_id=h.user_id,
            problem_id=h.problem_id,
            diagnosis_id=h.diagnosis_id,
            hint_level=h.hint_level,
            hint_tier_name=TIER_NAMES.get(h.hint_level, f"Level {h.hint_level}"),
            hint_title=h.hint_title,
            hint_content=h.hint_content,
            penalty_score=h.penalty_score,
            leak_check_passed=h.leak_check_passed,
            created_at=h.created_at,
        )
        for h in sorted_hints
    ]

    total_penalty = round(sum(h.penalty_score for h in hint_responses), 2)
    max_unlocked = max([h.hint_level for h in hint_responses], default=0)

    return HintListResponse(
        submission_id=submission.id,
        total_penalty=total_penalty,
        max_unlocked_level=max_unlocked,
        hints=hint_responses,
    )
