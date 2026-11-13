"""Human-in-the-Loop Annotation Queue API endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.core.dependencies import require_role
from backend.app.database import get_db
from backend.app.models.annotation import AnnotationTask, AnnotationTaskStatus
from backend.app.models.misconception import DetectorType, Diagnosis, MisconceptionTaxonomy
from backend.app.models.submission import Submission
from backend.app.models.user import User, UserRole
from backend.app.schemas.annotation import (
    AnnotationQueueResponse,
    AnnotationResolveRequest,
    AnnotationTaskResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

router = APIRouter(prefix="/annotations", tags=["Human Annotation Queue"])


def _build_task_response(task: AnnotationTask) -> AnnotationTaskResponse:
    """Helper to assemble an AnnotationTaskResponse with joined submission/problem context."""
    sub = task.submission
    student_id = sub.user_id if sub else None
    student_name = sub.user.full_name if (sub and sub.user) else None
    problem_id = sub.problem_id if sub else None
    problem_title = sub.problem.title if (sub and sub.problem) else None
    submission_code = sub.code if sub else None

    return AnnotationTaskResponse(
        id=task.id,
        submission_id=task.submission_id,
        diagnosis_id=task.diagnosis_id,
        status=task.status,
        assigned_annotator_id=task.assigned_annotator_id,
        original_misconception_code=task.original_misconception_code,
        original_confidence=task.original_confidence,
        trigger_reason=task.trigger_reason,
        resolved_misconception_code=task.resolved_misconception_code,
        annotator_notes=task.annotator_notes,
        resolved_at=task.resolved_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        student_id=student_id,
        student_name=student_name,
        problem_id=problem_id,
        problem_title=problem_title,
        submission_code=submission_code,
    )


@router.get(
    "/queue",
    response_model=AnnotationQueueResponse,
    summary="List review tasks awaiting human verification",
)
async def get_annotation_queue(
    status_filter: Optional[AnnotationTaskStatus] = Query(
        default=AnnotationTaskStatus.PENDING,
        description="Filter tasks by status (e.g. PENDING, RESOLVED, DISMISSED)",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(
        require_role(UserRole.ANNOTATOR, UserRole.ADMIN, UserRole.TEACHER)
    ),
    db: AsyncSession = Depends(get_db),
) -> AnnotationQueueResponse:
    """Retrieve annotation queue tasks. Restricted to ANNOTATOR, TEACHER, and ADMIN roles."""
    count_stmt = select(func.count(AnnotationTask.id))
    if status_filter:
        count_stmt = count_stmt.where(AnnotationTask.status == status_filter)

    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    query = (
        select(AnnotationTask)
        .options(
            joinedload(AnnotationTask.submission).joinedload(Submission.user),
            joinedload(AnnotationTask.submission).joinedload(Submission.problem),
        )
        .order_by(AnnotationTask.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if status_filter:
        query = query.where(AnnotationTask.status == status_filter)

    res = await db.execute(query)
    tasks = res.scalars().all()

    return AnnotationQueueResponse(
        total_pending=total_count,
        tasks=[_build_task_response(t) for t in tasks],
    )


@router.get(
    "/{task_id}",
    response_model=AnnotationTaskResponse,
    summary="Retrieve details of a single annotation task",
)
async def get_annotation_task(
    task_id: uuid.UUID,
    current_user: User = Depends(
        require_role(UserRole.ANNOTATOR, UserRole.ADMIN, UserRole.TEACHER)
    ),
    db: AsyncSession = Depends(get_db),
) -> AnnotationTaskResponse:
    """Retrieve full details of an annotation task including student code and context."""
    query = (
        select(AnnotationTask)
        .options(
            joinedload(AnnotationTask.submission).joinedload(Submission.user),
            joinedload(AnnotationTask.submission).joinedload(Submission.problem),
        )
        .where(AnnotationTask.id == task_id)
    )
    res = await db.execute(query)
    task = res.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation task not found.",
        )

    return _build_task_response(task)


@router.post(
    "/{task_id}/resolve",
    response_model=AnnotationTaskResponse,
    summary="Resolve annotation task with human ground-truth misconception override",
)
async def resolve_annotation_task(
    task_id: uuid.UUID,
    payload: AnnotationResolveRequest,
    current_user: User = Depends(
        require_role(UserRole.ANNOTATOR, UserRole.ADMIN, UserRole.TEACHER)
    ),
    db: AsyncSession = Depends(get_db),
) -> AnnotationTaskResponse:
    """Provide human diagnosis override. Updates diagnosis record to confidence=1.0."""
    # Verify taxonomy code exists
    tax_res = await db.execute(
        select(MisconceptionTaxonomy).where(
            MisconceptionTaxonomy.code == payload.resolved_misconception_code
        )
    )
    tax = tax_res.scalar_one_or_none()
    if not tax:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown misconception taxonomy code: {payload.resolved_misconception_code}",
        )

    query = (
        select(AnnotationTask)
        .options(
            joinedload(AnnotationTask.submission).joinedload(Submission.user),
            joinedload(AnnotationTask.submission).joinedload(Submission.problem),
        )
        .where(AnnotationTask.id == task_id)
    )
    res = await db.execute(query)
    task = res.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation task not found.",
        )

    task.status = AnnotationTaskStatus.RESOLVED
    task.assigned_annotator_id = current_user.id
    task.resolved_misconception_code = payload.resolved_misconception_code
    task.annotator_notes = payload.annotator_notes
    task.resolved_at = datetime.now(timezone.utc)

    # Propagate override to associated Diagnosis
    if task.diagnosis_id:
        diag_res = await db.execute(
            select(Diagnosis).where(Diagnosis.id == task.diagnosis_id)
        )
        diag = diag_res.scalar_one_or_none()
        if diag:
            diag.misconception_code = payload.resolved_misconception_code
            diag.confidence_score = 1.0
            diag.detector_type = DetectorType.HUMAN_OVERRIDE
            override_msg = (
                f"Human verified override by {current_user.full_name} ({current_user.email})"
            )
            if payload.annotator_notes:
                override_msg += f": {payload.annotator_notes}"
            diag.explanation = (
                f"{diag.explanation}\n[HUMAN_OVERRIDE]: {override_msg}"
                if diag.explanation
                else override_msg
            )

    await db.commit()
    await db.refresh(task)

    return _build_task_response(task)


@router.post(
    "/{task_id}/dismiss",
    response_model=AnnotationTaskResponse,
    summary="Dismiss an annotation task as not requiring reclassification",
)
async def dismiss_annotation_task(
    task_id: uuid.UUID,
    notes: Optional[str] = Query(default=None, description="Optional dismissal justification"),
    current_user: User = Depends(
        require_role(UserRole.ANNOTATOR, UserRole.ADMIN, UserRole.TEACHER)
    ),
    db: AsyncSession = Depends(get_db),
) -> AnnotationTaskResponse:
    """Dismiss a pending task from the queue without modifying original diagnosis."""
    query = (
        select(AnnotationTask)
        .options(
            joinedload(AnnotationTask.submission).joinedload(Submission.user),
            joinedload(AnnotationTask.submission).joinedload(Submission.problem),
        )
        .where(AnnotationTask.id == task_id)
    )
    res = await db.execute(query)
    task = res.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation task not found.",
        )

    task.status = AnnotationTaskStatus.DISMISSED
    task.assigned_annotator_id = current_user.id
    if notes:
        task.annotator_notes = notes
    task.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)

    return _build_task_response(task)
