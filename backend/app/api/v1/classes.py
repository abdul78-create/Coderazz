"""Class roster and student enrollment API endpoints."""

import uuid
from typing import List

from backend.app.core.dependencies import get_current_user, require_role
from backend.app.database import get_db
from backend.app.models.hint import HintRequest
from backend.app.models.roster import ClassEnrollment, ClassGroup, generate_join_code
from backend.app.models.submission import Submission
from backend.app.models.user import User, UserRole
from backend.app.schemas.roster import (
    ClassGroupCreate,
    ClassGroupResponse,
    ClassJoinRequest,
    ClassRosterResponse,
    EnrollmentResponse,
    RosterStudentItem,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/classes", tags=["Class Rosters & Enrollments"])


@router.post(
    "",
    response_model=ClassGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new class group (Teacher only)",
)
async def create_class(
    payload: ClassGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
) -> ClassGroupResponse:
    """Create a new class group and generate an enrollment join code."""
    # Ensure unique join code
    join_code = generate_join_code()
    for _ in range(5):
        existing = await db.execute(select(ClassGroup).where(ClassGroup.join_code == join_code))
        if existing.scalar_one_or_none() is None:
            break
        join_code = generate_join_code()

    new_class = ClassGroup(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        join_code=join_code,
        teacher_id=current_user.id,
        is_active=True,
    )
    db.add(new_class)
    await db.commit()
    await db.refresh(new_class)

    return ClassGroupResponse(
        id=new_class.id,
        name=new_class.name,
        description=new_class.description,
        join_code=new_class.join_code,
        teacher_id=new_class.teacher_id,
        teacher_name=current_user.full_name,
        is_active=new_class.is_active,
        student_count=0,
        created_at=new_class.created_at,
        updated_at=new_class.updated_at,
    )


@router.get(
    "",
    response_model=List[ClassGroupResponse],
    summary="List classes relevant to the current user",
)
async def list_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ClassGroupResponse]:
    """List classes: teachers see classes they own; students see classes they joined."""
    if current_user.role in (UserRole.TEACHER, UserRole.ADMIN):
        # Query classes taught by this teacher
        stmt = (
            select(
                ClassGroup,
                func.count(ClassEnrollment.id).label("student_count"),
            )
            .outerjoin(ClassEnrollment, ClassGroup.id == ClassEnrollment.class_id)
            .where(
                ClassGroup.teacher_id == current_user.id
                if current_user.role == UserRole.TEACHER
                else True
            )
            .group_by(ClassGroup.id)
            .order_by(ClassGroup.created_at.desc())
        )
        res = await db.execute(stmt)
        rows = res.all()

        return [
            ClassGroupResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                join_code=c.join_code,
                teacher_id=c.teacher_id,
                teacher_name=current_user.full_name,
                is_active=c.is_active,
                student_count=count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c, count in rows
        ]

    # Student role: query classes student is enrolled in
    stmt = (
        select(ClassGroup, User.full_name.label("teacher_name"))
        .join(ClassEnrollment, ClassGroup.id == ClassEnrollment.class_id)
        .join(User, ClassGroup.teacher_id == User.id)
        .where(
            ClassEnrollment.student_id == current_user.id,
            ClassEnrollment.is_active.is_(True),
        )
        .order_by(ClassEnrollment.enrolled_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    results: List[ClassGroupResponse] = []
    for c, teacher_name in rows:
        cnt_res = await db.execute(
            select(func.count(ClassEnrollment.id)).where(
                ClassEnrollment.class_id == c.id,
                ClassEnrollment.is_active.is_(True),
            )
        )
        count = cnt_res.scalar_one()
        results.append(
            ClassGroupResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                join_code=c.join_code,
                teacher_id=c.teacher_id,
                teacher_name=teacher_name,
                is_active=c.is_active,
                student_count=count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return results


@router.post(
    "/join",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join a class via join code (Student)",
)
async def join_class(
    payload: ClassJoinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnrollmentResponse:
    """Enroll the authenticated student into a class group using its 6-character code."""
    normalized_code = payload.join_code.strip().upper()

    stmt = (
        select(ClassGroup)
        .where(ClassGroup.join_code == normalized_code)
        .options(selectinload(ClassGroup.teacher))
    )
    res = await db.execute(stmt)
    class_group = res.scalar_one_or_none()

    if not class_group or not class_group.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or inactive class join code.",
        )

    # Check if student is already enrolled
    enr_check = await db.execute(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == class_group.id,
            ClassEnrollment.student_id == current_user.id,
        )
    )
    existing_enr = enr_check.scalar_one_or_none()
    if existing_enr:
        if existing_enr.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already enrolled in this class.",
            )
        # Reactivate enrollment
        existing_enr.is_active = True
        await db.commit()
        await db.refresh(existing_enr)
        return EnrollmentResponse(
            id=existing_enr.id,
            class_id=class_group.id,
            class_name=class_group.name,
            teacher_name=class_group.teacher.full_name if class_group.teacher else "Teacher",
            student_id=current_user.id,
            student_name=current_user.full_name,
            student_email=current_user.email,
            enrolled_at=existing_enr.enrolled_at,
            is_active=existing_enr.is_active,
        )

    new_enrollment = ClassEnrollment(
        class_id=class_group.id,
        student_id=current_user.id,
        is_active=True,
    )
    db.add(new_enrollment)
    await db.commit()
    await db.refresh(new_enrollment)

    return EnrollmentResponse(
        id=new_enrollment.id,
        class_id=class_group.id,
        class_name=class_group.name,
        teacher_name=class_group.teacher.full_name if class_group.teacher else "Teacher",
        student_id=current_user.id,
        student_name=current_user.full_name,
        student_email=current_user.email,
        enrolled_at=new_enrollment.enrolled_at,
        is_active=new_enrollment.is_active,
    )


@router.get(
    "/{class_id}",
    response_model=ClassGroupResponse,
    summary="Get single class group details",
)
async def get_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClassGroupResponse:
    """Retrieve class details.

    Authorized only if current user is the owner teacher, an admin, or an enrolled student.
    """
    stmt = (
        select(ClassGroup)
        .where(ClassGroup.id == class_id)
        .options(selectinload(ClassGroup.teacher))
    )
    res = await db.execute(stmt)
    class_group = res.scalar_one_or_none()

    if not class_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class group not found.",
        )

    # Permission verification
    is_teacher_owner = class_group.teacher_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN

    if not is_teacher_owner and not is_admin:
        # Check if student is enrolled
        enr_stmt = select(ClassEnrollment).where(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.student_id == current_user.id,
            ClassEnrollment.is_active.is_(True),
        )
        enr_res = await db.execute(enr_stmt)
        if enr_res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this class.",
            )

    count_res = await db.execute(
        select(func.count(ClassEnrollment.id)).where(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.is_active.is_(True),
        )
    )
    student_count = count_res.scalar_one()

    return ClassGroupResponse(
        id=class_group.id,
        name=class_group.name,
        description=class_group.description,
        join_code=class_group.join_code,
        teacher_id=class_group.teacher_id,
        teacher_name=class_group.teacher.full_name if class_group.teacher else "Teacher",
        is_active=class_group.is_active,
        student_count=student_count,
        created_at=class_group.created_at,
        updated_at=class_group.updated_at,
    )


@router.get(
    "/{class_id}/roster",
    response_model=ClassRosterResponse,
    summary="Get class roster with student diagnostic metrics (Teacher only)",
)
async def get_class_roster(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
) -> ClassRosterResponse:
    """Retrieve full student roster with submission and hint stats for the class teacher."""
    stmt = (
        select(ClassGroup)
        .where(ClassGroup.id == class_id)
        .options(selectinload(ClassGroup.teacher))
    )
    res = await db.execute(stmt)
    class_group = res.scalar_one_or_none()

    if not class_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class group not found.",
        )

    # Ownership check: teachers can only view rosters for their own classes
    if current_user.role == UserRole.TEACHER and class_group.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view another teacher's class roster.",
        )

    # Fetch enrolled students
    enr_stmt = (
        select(ClassEnrollment, User)
        .join(User, ClassEnrollment.student_id == User.id)
        .where(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.is_active.is_(True),
        )
        .order_by(User.full_name.asc())
    )
    enr_res = await db.execute(enr_stmt)
    enr_rows = enr_res.all()

    student_items: List[RosterStudentItem] = []
    for enr, student in enr_rows:
        # Aggregate submissions count for this student
        sub_cnt = await db.execute(
            select(func.count(Submission.id)).where(Submission.user_id == student.id)
        )
        submissions_count = sub_cnt.scalar_one()

        # Aggregate hints unlocked and penalty scores
        hint_res = await db.execute(
            select(
                func.count(HintRequest.id),
                func.coalesce(func.sum(HintRequest.penalty_score), 0.0),
            ).where(HintRequest.user_id == student.id)
        )
        total_hints, total_penalty = hint_res.one()

        student_items.append(
            RosterStudentItem(
                student_id=student.id,
                full_name=student.full_name,
                email=student.email,
                enrolled_at=enr.enrolled_at,
                submissions_count=submissions_count,
                total_hints_unlocked=total_hints,
                total_penalty=round(float(total_penalty), 2),
            )
        )

    class_resp = ClassGroupResponse(
        id=class_group.id,
        name=class_group.name,
        description=class_group.description,
        join_code=class_group.join_code,
        teacher_id=class_group.teacher_id,
        teacher_name=class_group.teacher.full_name if class_group.teacher else "Teacher",
        is_active=class_group.is_active,
        student_count=len(student_items),
        created_at=class_group.created_at,
        updated_at=class_group.updated_at,
    )

    return ClassRosterResponse(
        class_group=class_resp,
        students=student_items,
    )
