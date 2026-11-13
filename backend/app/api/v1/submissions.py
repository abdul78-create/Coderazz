"""Code execution and submission API endpoints."""

import uuid
from typing import List, Optional

from backend.app.core.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models.misconception import Diagnosis, MisconceptionTaxonomy
from backend.app.models.problem import Problem, TestCase
from backend.app.models.submission import Submission, SubmissionStatus, SubmissionVerdict
from backend.app.models.user import User, UserRole
from backend.app.schemas.submission import (
    CodeRunRequest,
    CodeRunResponse,
    DiagnosisResponse,
    SubmissionCreateRequest,
    SubmissionListItemResponse,
    SubmissionResponse,
)
from backend.app.services.sandbox import (
    SandboxUnavailableException,
    TestCaseExecutionResult,
    sandbox_service,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from ml.fusion import FusedDiagnosis, MisconceptionFusionEngine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/submissions", tags=["Code Execution & Submissions"])
fusion_engine = MisconceptionFusionEngine()


async def _diagnose_and_build_response(
    code: str,
    db: AsyncSession,
) -> tuple[FusedDiagnosis, DiagnosisResponse]:
    """Diagnose code through the Fusion Engine and enrich with taxonomy metadata."""
    fused = await fusion_engine.diagnose(source_code=code, sandbox=sandbox_service)
    tax_query = select(MisconceptionTaxonomy).where(
        MisconceptionTaxonomy.code == fused.misconception_code
    )
    tax_res = await db.execute(tax_query)
    taxonomy = tax_res.scalar_one_or_none()

    detector_str = (
        fused.detector_type.value
        if hasattr(fused.detector_type, "value")
        else str(fused.detector_type)
    )

    diag_resp = DiagnosisResponse(
        misconception_code=fused.misconception_code,
        misconception_name=taxonomy.name if taxonomy else fused.misconception_code,
        misconception_category=taxonomy.category if taxonomy else "General",
        confidence_score=fused.confidence,
        detector_type=detector_str,
        is_primary=True,
        evidence_lines=fused.evidence_lines,
        explanation=fused.explanation,
        pedagogical_remedy=taxonomy.pedagogical_remedy if taxonomy else None,
        secondary_candidates=fused.secondary_candidates,
    )
    return fused, diag_resp


@router.post(
    "/run",
    response_model=CodeRunResponse,
    summary="Run code interactively against sample test cases (Sandbox)",
)
async def run_code_interactively(
    payload: CodeRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CodeRunResponse:
    """Execute code in the disposable Docker container against sample test cases or custom input."""
    # 1. Custom input execution
    if payload.custom_input is not None:
        try:
            run_result = await sandbox_service.execute_code_once(
                code=payload.code,
                input_data=payload.custom_input,
            )
        except SandboxUnavailableException as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        diag_custom: Optional[DiagnosisResponse] = None
        if run_result.verdict != SubmissionVerdict.ACCEPTED:
            try:
                _, diag_custom = await _diagnose_and_build_response(payload.code, db)
            except Exception:
                pass

        return CodeRunResponse(
            verdict=run_result.verdict,
            stdout=run_result.stdout,
            stderr=run_result.stderr,
            runtime_ms=run_result.runtime_ms,
            memory_kb=run_result.memory_kb,
            test_cases_passed=1 if run_result.verdict == SubmissionVerdict.ACCEPTED else 0,
            total_test_cases=1,
            error_message=run_result.error_message,
            test_cases=[
                TestCaseExecutionResult(
                    order_index=1,
                    is_hidden=False,
                    passed=run_result.verdict == SubmissionVerdict.ACCEPTED,
                    verdict=run_result.verdict,
                    runtime_ms=run_result.runtime_ms,
                    memory_kb=run_result.memory_kb,
                    input_data=payload.custom_input,
                    expected_output=None,
                    actual_output=run_result.stdout.strip(),
                    stderr=run_result.stderr,
                )
            ],
            diagnosis=diag_custom,
        )

    # 2. Problem sample test cases execution
    if not payload.problem_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either problem_id or custom_input must be provided.",
        )

    prob_query = (
        select(Problem)
        .options(selectinload(Problem.test_cases))
        .where(Problem.id == payload.problem_id)
    )
    res = await db.execute(prob_query)
    problem = res.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )

    # Only run against visible sample test cases
    sample_cases = [tc for tc in problem.test_cases if not tc.is_hidden]
    if not sample_cases:
        # Fallback to single dummy input if no sample test cases exist
        sample_cases = [
            TestCase(
                problem_id=problem.id,
                input_data="",
                expected_output="",
                is_hidden=False,
                order_index=1,
            )
        ]

    try:
        summary = await sandbox_service.evaluate_test_cases(
            code=payload.code,
            test_cases=sample_cases,
            stop_on_first_failure=False,
            timeout_seconds=float(problem.time_limit_ms) / 1000.0,
        )
    except SandboxUnavailableException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    first_err = summary.first_failing_test_case.stderr if summary.first_failing_test_case else None

    diag_sample: Optional[DiagnosisResponse] = None
    if summary.overall_verdict != SubmissionVerdict.ACCEPTED:
        try:
            _, diag_sample = await _diagnose_and_build_response(payload.code, db)
        except Exception:
            pass

    return CodeRunResponse(
        verdict=summary.overall_verdict,
        stdout=(
            summary.test_case_results[0].actual_output or ""
            if summary.test_case_results
            else ""
        ),
        stderr=first_err or "",
        runtime_ms=summary.max_runtime_ms,
        memory_kb=summary.max_memory_kb,
        test_cases_passed=summary.test_cases_passed,
        total_test_cases=summary.total_test_cases,
        error_message=first_err,
        test_cases=summary.test_case_results,
        diagnosis=diag_sample,
    )


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for final grading and save to history",
)
async def submit_code(
    payload: SubmissionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """Submit code against all test cases in the sandbox and record the submission."""
    prob_query = (
        select(Problem)
        .options(selectinload(Problem.test_cases))
        .where(Problem.id == payload.problem_id)
    )
    res = await db.execute(prob_query)
    problem = res.scalar_one_or_none()

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found.",
        )

    all_cases = problem.test_cases
    if not all_cases:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Problem has no evaluation test cases configured.",
        )

    # Execute inside isolated disposable Docker sandbox
    try:
        summary = await sandbox_service.evaluate_test_cases(
            code=payload.code,
            test_cases=all_cases,
            stop_on_first_failure=True,  # Competitive programming standard: stop on first failure
            timeout_seconds=float(problem.time_limit_ms) / 1000.0,
        )
    except SandboxUnavailableException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # Assemble summary error message
    err_msg = None
    if summary.first_failing_test_case:
        tc = summary.first_failing_test_case
        if tc.verdict == SubmissionVerdict.WRONG_ANSWER:
            err_msg = f"Wrong Answer on test case {tc.order_index}."
        elif tc.verdict == SubmissionVerdict.TIME_LIMIT_EXCEEDED:
            err_msg = f"Time Limit Exceeded on test case {tc.order_index} (3.0s limit)."
        elif tc.verdict == SubmissionVerdict.MEMORY_LIMIT_EXCEEDED:
            err_msg = f"Memory Limit Exceeded on test case {tc.order_index} (128 MB limit)."
        elif tc.stderr:
            err_msg = tc.stderr[:1000]

    # Create submission record
    new_submission = Submission(
        user_id=current_user.id,
        problem_id=problem.id,
        code=payload.code,
        language=payload.language,
        status=SubmissionStatus.COMPLETED,
        verdict=summary.overall_verdict,
        runtime_ms=summary.max_runtime_ms,
        memory_kb=summary.max_memory_kb,
        test_cases_passed=summary.test_cases_passed,
        total_test_cases=len(all_cases),
        stdout=(
            summary.test_case_results[0].actual_output
            if summary.test_case_results and not summary.test_case_results[0].is_hidden
            else None
        ),
        stderr=err_msg,
        error_message=err_msg,
    )
    db.add(new_submission)
    await db.commit()
    await db.refresh(new_submission)

    # If submission failed evaluation, diagnose misconception and persist to database
    diag_record: Optional[DiagnosisResponse] = None
    if summary.overall_verdict != SubmissionVerdict.ACCEPTED:
        try:
            fused, diag_record = await _diagnose_and_build_response(payload.code, db)
            db_diagnosis = Diagnosis(
                submission_id=new_submission.id,
                misconception_code=fused.misconception_code,
                confidence_score=fused.confidence,
                detector_type=fused.detector_type,
                is_primary=True,
                evidence_lines=fused.evidence_lines,
                explanation=fused.explanation,
                metadata_json=fused.metadata,
            )
            db.add(db_diagnosis)
            await db.commit()
            await db.refresh(db_diagnosis)
            diag_record.id = db_diagnosis.id
        except Exception:
            pass

    return SubmissionResponse(
        id=new_submission.id,
        problem_id=problem.id,
        user_id=current_user.id,
        code=new_submission.code,
        language=new_submission.language,
        status=new_submission.status,
        verdict=new_submission.verdict,
        runtime_ms=new_submission.runtime_ms,
        memory_kb=new_submission.memory_kb,
        test_cases_passed=new_submission.test_cases_passed,
        total_test_cases=new_submission.total_test_cases,
        stdout=new_submission.stdout,
        stderr=new_submission.stderr,
        error_message=new_submission.error_message,
        created_at=new_submission.created_at,
        problem_title=problem.title,
        problem_slug=problem.slug,
        diagnosis=diag_record,
        diagnoses=[diag_record] if diag_record else [],
    )


@router.get(
    "",
    response_model=List[SubmissionListItemResponse],
    summary="List user's submission history",
)
async def list_submissions(
    problem_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[SubmissionListItemResponse]:
    """Retrieve history of submissions. Students only see their own submissions."""
    query = (
        select(Submission, Problem.title, Problem.slug)
        .join(Problem, Submission.problem_id == Problem.id)
        .where(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
        .limit(limit)
    )

    if problem_id:
        query = query.where(Submission.problem_id == problem_id)

    result = await db.execute(query)
    rows = result.all()

    items: List[SubmissionListItemResponse] = []
    for sub, prob_title, prob_slug in rows:
        item = SubmissionListItemResponse(
            id=sub.id,
            problem_id=sub.problem_id,
            problem_title=prob_title,
            problem_slug=prob_slug,
            verdict=sub.verdict,
            status=sub.status,
            runtime_ms=sub.runtime_ms,
            test_cases_passed=sub.test_cases_passed,
            total_test_cases=sub.total_test_cases,
            created_at=sub.created_at,
        )
        items.append(item)

    return items


@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get single submission details (RBAC protected)",
)
async def get_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    """Retrieve details for a specific submission. Prevents cross-student data exfiltration."""
    query = (
        select(Submission, Problem.title, Problem.slug)
        .join(Problem, Submission.problem_id == Problem.id)
        .options(
            selectinload(Submission.diagnoses).selectinload(Diagnosis.misconception)
        )
        .where(Submission.id == submission_id)
    )
    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    sub, prob_title, prob_slug = row

    # Cross-user authorization check: Students can only view their own submissions
    if current_user.role == UserRole.STUDENT and sub.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access denied: You do not have permission to view "
                "another student's submission."
            ),
        )

    diagnoses_resp: List[DiagnosisResponse] = []
    primary_diag: Optional[DiagnosisResponse] = None
    for d in sub.diagnoses:
        d_resp = DiagnosisResponse(
            id=d.id,
            misconception_code=d.misconception_code,
            misconception_name=d.misconception.name if d.misconception else d.misconception_code,
            misconception_category=d.misconception.category if d.misconception else "General",
            confidence_score=d.confidence_score,
            detector_type=(
                d.detector_type.value
                if hasattr(d.detector_type, "value")
                else str(d.detector_type)
            ),
            is_primary=d.is_primary,
            evidence_lines=d.evidence_lines,
            explanation=d.explanation,
            pedagogical_remedy=d.misconception.pedagogical_remedy if d.misconception else None,
        )
        diagnoses_resp.append(d_resp)
        if d.is_primary and primary_diag is None:
            primary_diag = d_resp

    return SubmissionResponse(
        id=sub.id,
        problem_id=sub.problem_id,
        user_id=sub.user_id,
        code=sub.code,
        language=sub.language,
        status=sub.status,
        verdict=sub.verdict,
        runtime_ms=sub.runtime_ms,
        memory_kb=sub.memory_kb,
        test_cases_passed=sub.test_cases_passed,
        total_test_cases=sub.total_test_cases,
        stdout=sub.stdout,
        stderr=sub.stderr,
        error_message=sub.error_message,
        created_at=sub.created_at,
        problem_title=prob_title,
        problem_slug=prob_slug,
        diagnosis=primary_diag or (diagnoses_resp[0] if diagnoses_resp else None),
        diagnoses=diagnoses_resp,
    )
