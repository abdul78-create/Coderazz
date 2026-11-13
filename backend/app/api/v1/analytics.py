"""Teacher Analytics and Class-wide Struggle Trends API endpoints."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from backend.app.core.dependencies import require_role
from backend.app.database import get_db
from backend.app.models.hint import HintRequest
from backend.app.models.misconception import Diagnosis, MisconceptionTaxonomy
from backend.app.models.roster import ClassEnrollment, ClassGroup
from backend.app.models.submission import Submission, SubmissionVerdict
from backend.app.models.user import User, UserRole
from backend.app.schemas.analytics import (
    ClassMisconceptionAnalyticsResponse,
    ClassStruggleTrendsResponse,
    DailyStrugglePoint,
    MisconceptionFrequencyItem,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/classes/{class_id}/analytics", tags=["Teacher Analytics"])


async def _verify_teacher_class_access(
    class_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
) -> ClassGroup:
    """Verify class existence and ensure only the owner teacher or admin has access."""
    res = await db.execute(select(ClassGroup).where(ClassGroup.id == class_id))
    class_group = res.scalar_one_or_none()

    if not class_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class group not found.",
        )

    if current_user.role == UserRole.TEACHER and class_group.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view analytics for another teacher's class.",
        )

    return class_group


@router.get(
    "/misconceptions",
    response_model=ClassMisconceptionAnalyticsResponse,
    summary="Aggregate class-wide misconception prevalence",
)
async def get_class_misconceptions(
    class_id: uuid.UUID,
    problem_id: Optional[uuid.UUID] = Query(None, description="Optional problem filter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
) -> ClassMisconceptionAnalyticsResponse:
    """Aggregate frequency, unique student impact, and severity of misconceptions for a class."""
    class_group = await _verify_teacher_class_access(class_id, db, current_user)

    # Fetch active enrolled student IDs
    enr_res = await db.execute(
        select(ClassEnrollment.student_id).where(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.is_active.is_(True),
        )
    )
    student_ids = [row[0] for row in enr_res.all()]

    if not student_ids:
        return ClassMisconceptionAnalyticsResponse(
            class_id=class_group.id,
            class_name=class_group.name,
            problem_id=problem_id,
            total_diagnoses=0,
            total_students_diagnosed=0,
            misconceptions=[],
        )

    # Build aggregation query
    conditions = [
        Submission.user_id.in_(student_ids),
        Diagnosis.is_primary.is_(True),
    ]
    if problem_id:
        conditions.append(Submission.problem_id == problem_id)

    stmt = (
        select(
            Diagnosis.misconception_code,
            MisconceptionTaxonomy.name,
            MisconceptionTaxonomy.category,
            MisconceptionTaxonomy.severity,
            func.count(Diagnosis.id).label("freq"),
            func.count(func.distinct(Submission.user_id)).label("unique_students"),
        )
        .join(Submission, Diagnosis.submission_id == Submission.id)
        .join(MisconceptionTaxonomy, Diagnosis.misconception_code == MisconceptionTaxonomy.code)
        .where(*conditions)
        .group_by(
            Diagnosis.misconception_code,
            MisconceptionTaxonomy.name,
            MisconceptionTaxonomy.category,
            MisconceptionTaxonomy.severity,
        )
        .order_by(func.count(Diagnosis.id).desc())
    )
    rows = (await db.execute(stmt)).all()

    total_diagnoses = sum(r[4] for r in rows)

    # Distinct students affected across all misconceptions
    unique_stud_stmt = (
        select(func.count(func.distinct(Submission.user_id)))
        .join(Diagnosis, Diagnosis.submission_id == Submission.id)
        .where(*conditions)
    )
    total_unique_students = (await db.execute(unique_stud_stmt)).scalar_one()

    items = [
        MisconceptionFrequencyItem(
            misconception_code=code,
            misconception_name=name,
            category=category,
            severity=severity,
            count=count,
            unique_students=unique_students,
            percentage=round((count / total_diagnoses) * 100, 1) if total_diagnoses > 0 else 0.0,
        )
        for code, name, category, severity, count, unique_students in rows
    ]

    return ClassMisconceptionAnalyticsResponse(
        class_id=class_group.id,
        class_name=class_group.name,
        problem_id=problem_id,
        total_diagnoses=total_diagnoses,
        total_students_diagnosed=total_unique_students,
        misconceptions=items,
    )


@router.get(
    "/struggle-trends",
    response_model=ClassStruggleTrendsResponse,
    summary="Daily time-series of submissions, hints, and active students",
)
async def get_class_struggle_trends(
    class_id: uuid.UUID,
    days: int = Query(14, ge=1, le=90, description="Time window in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
) -> ClassStruggleTrendsResponse:
    """Return daily longitudinal struggle trends for teacher dashboard charts."""
    class_group = await _verify_teacher_class_access(class_id, db, current_user)

    enr_res = await db.execute(
        select(ClassEnrollment.student_id).where(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.is_active.is_(True),
        )
    )
    student_ids = [row[0] for row in enr_res.all()]

    if not student_ids:
        return ClassStruggleTrendsResponse(
            class_id=class_group.id,
            class_name=class_group.name,
            time_window_days=days,
            total_submissions=0,
            total_hints=0,
            trend=[],
        )

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 1. Submissions & active students grouped by date
    sub_stmt = (
        select(
            func.date(Submission.created_at).label("day"),
            func.count(Submission.id).label("sub_count"),
            func.count(func.distinct(Submission.user_id)).label("unique_students"),
            func.sum(
                case(
                    (Submission.verdict != SubmissionVerdict.ACCEPTED, 1),
                    else_=0,
                )
            ).label("fail_count"),
        )
        .where(
            Submission.user_id.in_(student_ids),
            Submission.created_at >= cutoff,
        )
        .group_by(func.date(Submission.created_at))
        .order_by(func.date(Submission.created_at).asc())
    )
    sub_rows = (await db.execute(sub_stmt)).all()

    # 2. Hints grouped by date
    hint_stmt = (
        select(
            func.date(HintRequest.created_at).label("day"),
            func.count(HintRequest.id).label("hint_count"),
        )
        .where(
            HintRequest.user_id.in_(student_ids),
            HintRequest.created_at >= cutoff,
        )
        .group_by(func.date(HintRequest.created_at))
    )
    hint_rows = (await db.execute(hint_stmt)).all()
    hints_by_day = {str(r[0]): r[1] for r in hint_rows}

    # 3. Diagnoses grouped by date
    diag_stmt = (
        select(
            func.date(Diagnosis.created_at).label("day"),
            func.count(Diagnosis.id).label("diag_count"),
        )
        .join(Submission, Diagnosis.submission_id == Submission.id)
        .where(
            Submission.user_id.in_(student_ids),
            Diagnosis.created_at >= cutoff,
        )
        .group_by(func.date(Diagnosis.created_at))
    )
    diag_rows = (await db.execute(diag_stmt)).all()
    diag_by_day = {str(r[0]): r[1] for r in diag_rows}

    daily_points: Dict[str, DailyStrugglePoint] = {}
    total_subs = 0

    for day_val, sub_cnt, unique_students, fail_cnt in sub_rows:
        day_str = str(day_val)
        total_subs += sub_cnt
        daily_points[day_str] = DailyStrugglePoint(
            date=day_str,
            submissions_count=sub_cnt,
            unique_students_active=unique_students,
            hints_requested_count=hints_by_day.get(day_str, 0),
            failing_submissions_count=int(fail_cnt or 0),
            diagnoses_count=diag_by_day.get(day_str, 0),
        )

    # Include days where hints were requested even without new submissions
    for day_str, h_cnt in hints_by_day.items():
        if day_str not in daily_points:
            daily_points[day_str] = DailyStrugglePoint(
                date=day_str,
                submissions_count=0,
                unique_students_active=0,
                hints_requested_count=h_cnt,
                failing_submissions_count=0,
                diagnoses_count=diag_by_day.get(day_str, 0),
            )

    sorted_trend = [daily_points[d] for d in sorted(daily_points.keys())]
    total_hints = sum(hints_by_day.values())

    return ClassStruggleTrendsResponse(
        class_id=class_group.id,
        class_name=class_group.name,
        time_window_days=days,
        total_submissions=total_subs,
        total_hints=total_hints,
        trend=sorted_trend,
    )
