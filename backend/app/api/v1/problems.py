"""Problem catalog and detail API endpoints."""

import uuid
from typing import List

from backend.app.core.dependencies import require_role
from backend.app.database import get_db
from backend.app.models.problem import Problem, ProblemDifficulty, TestCase
from backend.app.models.user import User, UserRole
from backend.app.schemas.problem import (
    ProblemCreateRequest,
    ProblemDetailResponse,
    ProblemListItemResponse,
    TestCasePublicResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/problems", tags=["Problems & Library"])


@router.get(
    "",
    response_model=List[ProblemListItemResponse],
    summary="List programming challenges in the catalog",
)
async def list_problems(
    difficulty: ProblemDifficulty | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> List[ProblemListItemResponse]:
    """Retrieve published programming problems for student practice."""
    # Query problems with test case counts
    query = (
        select(
            Problem,
            func.count(TestCase.id).label("total_cases"),
            func.count(TestCase.id).filter(TestCase.is_hidden.is_(False)).label("sample_cases"),
        )
        .outerjoin(TestCase, Problem.id == TestCase.problem_id)
        .where(Problem.is_published.is_(True))
        .group_by(Problem.id)
        .order_by(Problem.order_index, Problem.created_at)
    )

    if difficulty:
        query = query.where(Problem.difficulty == difficulty)
    if category:
        query = query.where(Problem.category.ilike(f"%{category}%"))

    result = await db.execute(query)
    rows = result.all()

    items: List[ProblemListItemResponse] = []
    for problem, total_cases, sample_cases in rows:
        item = ProblemListItemResponse(
            id=problem.id,
            slug=problem.slug,
            title=problem.title,
            difficulty=problem.difficulty,
            category=problem.category,
            order_index=problem.order_index,
            is_published=problem.is_published,
            sample_cases_count=sample_cases,
            total_cases_count=total_cases,
        )
        items.append(item)

    return items


@router.get(
    "/{id_or_slug}",
    response_model=ProblemDetailResponse,
    summary="Get problem details and visible sample test cases",
)
async def get_problem_details(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db),
) -> ProblemDetailResponse:
    """Retrieve problem details. Returns ONLY sample test cases (never hidden cases)."""
    # Check if id_or_slug is valid UUID
    is_uuid = False
    try:
        prob_uuid = uuid.UUID(id_or_slug)
        is_uuid = True
    except ValueError:
        is_uuid = False

    if is_uuid:
        query = (
            select(Problem)
            .options(selectinload(Problem.test_cases))
            .where(Problem.id == prob_uuid)
        )
    else:
        query = (
            select(Problem)
            .options(selectinload(Problem.test_cases))
            .where(Problem.slug == id_or_slug.lower().strip())
        )

    result = await db.execute(query)
    problem = result.scalar_one_or_none()

    if not problem or not problem.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{id_or_slug}' not found.",
        )

    # Filter to visible sample test cases ONLY
    sample_cases = [
        TestCasePublicResponse.model_validate(tc)
        for tc in problem.test_cases
        if not tc.is_hidden
    ]

    return ProblemDetailResponse(
        id=problem.id,
        slug=problem.slug,
        title=problem.title,
        description=problem.description,
        difficulty=problem.difficulty,
        category=problem.category,
        starter_code=problem.starter_code,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        order_index=problem.order_index,
        sample_test_cases=sample_cases,
    )


@router.post(
    "",
    response_model=ProblemDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new programming problem (Teachers & Admins only)",
)
async def create_problem(
    payload: ProblemCreateRequest,
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ProblemDetailResponse:
    """Allow educators and administrators to add a new problem with test cases."""
    # Check duplicate slug
    slug_query = select(Problem).where(Problem.slug == payload.slug)
    existing = await db.execute(slug_query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Problem with slug '{payload.slug}' already exists.",
        )

    new_problem = Problem(
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        difficulty=payload.difficulty,
        category=payload.category,
        starter_code=payload.starter_code,
        solution_template=payload.solution_template,
        time_limit_ms=payload.time_limit_ms,
        memory_limit_mb=payload.memory_limit_mb,
        order_index=payload.order_index,
    )
    db.add(new_problem)
    await db.flush()

    for idx, tc_data in enumerate(payload.test_cases):
        new_tc = TestCase(
            problem_id=new_problem.id,
            input_data=tc_data.input_data,
            expected_output=tc_data.expected_output,
            is_hidden=tc_data.is_hidden,
            explanation=tc_data.explanation,
            order_index=tc_data.order_index or (idx + 1),
        )
        db.add(new_tc)

    await db.commit()
    await db.refresh(new_problem)

    # Re-query with test_cases loaded
    query = (
        select(Problem)
        .options(selectinload(Problem.test_cases))
        .where(Problem.id == new_problem.id)
    )
    res = await db.execute(query)
    full_problem = res.scalar_one()

    sample_cases = [
        TestCasePublicResponse.model_validate(tc)
        for tc in full_problem.test_cases
        if not tc.is_hidden
    ]

    return ProblemDetailResponse(
        id=full_problem.id,
        slug=full_problem.slug,
        title=full_problem.title,
        description=full_problem.description,
        difficulty=full_problem.difficulty,
        category=full_problem.category,
        starter_code=full_problem.starter_code,
        time_limit_ms=full_problem.time_limit_ms,
        memory_limit_mb=full_problem.memory_limit_mb,
        order_index=full_problem.order_index,
        sample_test_cases=sample_cases,
    )
