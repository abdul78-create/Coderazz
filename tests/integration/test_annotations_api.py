"""Integration tests for Human-in-the-Loop Annotation Queue API endpoints."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.database import get_session_factory
from backend.app.main import app
from backend.app.models.annotation import AnnotationTask, AnnotationTaskStatus
from backend.app.models.misconception import DetectorType, Diagnosis
from backend.app.models.submission import (
    Submission,
    SubmissionStatus,
    SubmissionVerdict,
)


async def _get_auth_headers(
    client: AsyncClient,
    role: str = "student",
    name_prefix: str = "user",
) -> tuple[dict[str, str], dict]:
    """Helper to register and login a user, returning auth headers and profile dict."""
    email = f"{name_prefix}_{uuid.uuid4().hex[:8]}@coderazz.org"
    password = "SecurePassword#123"

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"{name_prefix.capitalize()} {role.capitalize()}",
            "role": role,
        },
    )
    assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    user_info = login_res.json()["user"]
    return {"Authorization": f"Bearer {token}"}, user_info


@pytest.mark.asyncio
async def test_annotation_endpoints_student_forbidden() -> None:
    """Verify that regular students are forbidden from accessing annotation queue endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        student_headers, _ = await _get_auth_headers(client, role="student", name_prefix="student_auth")

        dummy_uuid = str(uuid.uuid4())

        # 1. Access queue
        q_res = await client.get("/api/v1/annotations/queue", headers=student_headers)
        assert q_res.status_code == 403
        assert "Forbidden" in q_res.json()["detail"]

        # 2. Access single task
        t_res = await client.get(f"/api/v1/annotations/{dummy_uuid}", headers=student_headers)
        assert t_res.status_code == 403

        # 3. Resolve task
        r_res = await client.post(
            f"/api/v1/annotations/{dummy_uuid}/resolve",
            json={"resolved_misconception_code": "D4"},
            headers=student_headers,
        )
        assert r_res.status_code == 403

        # 4. Dismiss task
        d_res = await client.post(
            f"/api/v1/annotations/{dummy_uuid}/dismiss",
            headers=student_headers,
        )
        assert d_res.status_code == 403


@pytest.mark.asyncio
async def test_annotation_task_creation_and_resolve() -> None:
    """Verify annotation task queue inspection, contextual fields, and ground-truth override."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        teacher_headers, teacher_info = await _get_auth_headers(
            client, role="teacher", name_prefix="teacher_reviewer"
        )
        student_headers, student_info = await _get_auth_headers(
            client, role="student", name_prefix="student_author"
        )

        # Get seeded problem
        prob_res = await client.get("/api/v1/problems", headers=student_headers)
        problem = prob_res.json()[0]
        problem_id = uuid.UUID(problem["id"])
        student_id = uuid.UUID(student_info["id"])

        # Create a submission with low confidence diagnosis directly in DB to trigger task
        async with get_session_factory()() as session:
            sub = Submission(
                user_id=student_id,
                problem_id=problem_id,
                code="def solve():\n    return 'ambiguous'\n",
                language="python",
                status=SubmissionStatus.COMPLETED,
                verdict=SubmissionVerdict.WRONG_ANSWER,
                runtime_ms=12,
                memory_kb=1024,
                test_cases_passed=0,
                total_test_cases=3,
                error_message="Wrong Answer on test case 1.",
            )
            session.add(sub)
            await session.commit()
            await session.refresh(sub)

            diag = Diagnosis(
                submission_id=sub.id,
                misconception_code="S2",
                confidence_score=0.35,
                detector_type=DetectorType.ML_CLASSIFIER,
                is_primary=True,
                explanation="Low confidence novel pattern detected.",
            )
            session.add(diag)
            await session.commit()
            await session.refresh(diag)

            task = AnnotationTask(
                submission_id=sub.id,
                diagnosis_id=diag.id,
                status=AnnotationTaskStatus.PENDING,
                original_misconception_code="S2",
                original_confidence=0.35,
                trigger_reason="NOVEL_MISCONCEPTION (S2)",
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            task_id = str(task.id)

        # 1. Fetch queue as teacher
        queue_res = await client.get("/api/v1/annotations/queue", headers=teacher_headers)
        assert queue_res.status_code == 200
        queue_data = queue_res.json()
        assert queue_data["total_pending"] >= 1
        found_task = next((t for t in queue_data["tasks"] if t["id"] == task_id), None)
        assert found_task is not None
        assert found_task["original_misconception_code"] == "S2"
        assert found_task["problem_title"] == problem["title"]
        assert found_task["submission_code"] == "def solve():\n    return 'ambiguous'\n"

        # 2. Get specific task details
        detail_res = await client.get(f"/api/v1/annotations/{task_id}", headers=teacher_headers)
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["id"] == task_id
        assert detail_data["status"] == "PENDING"

        # 3. Resolve task with ground-truth override (e.g. D4)
        resolve_res = await client.post(
            f"/api/v1/annotations/{task_id}/resolve",
            json={
                "resolved_misconception_code": "D4",
                "annotator_notes": "Student prematurely returns inside loop.",
            },
            headers=teacher_headers,
        )
        assert resolve_res.status_code == 200
        resolved_data = resolve_res.json()
        assert resolved_data["status"] == "RESOLVED"
        assert resolved_data["resolved_misconception_code"] == "D4"
        assert resolved_data["annotator_notes"] == "Student prematurely returns inside loop."
        assert resolved_data["assigned_annotator_id"] == teacher_info["id"]
        assert resolved_data["resolved_at"] is not None

        # 4. Verify in DB that Diagnosis was updated with HUMAN_OVERRIDE and 1.0 confidence
        async with get_session_factory()() as session:
            diag_query = select(Diagnosis).where(Diagnosis.id == diag.id)
            diag_db = (await session.execute(diag_query)).scalar_one()
            assert diag_db.misconception_code == "D4"
            assert diag_db.confidence_score == 1.0
            assert diag_db.detector_type == DetectorType.HUMAN_OVERRIDE
            assert "HUMAN_OVERRIDE" in diag_db.explanation


@pytest.mark.asyncio
async def test_annotation_task_dismiss() -> None:
    """Verify dismissing an annotation task without modifying diagnosis."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        teacher_headers, teacher_info = await _get_auth_headers(
            client, role="teacher", name_prefix="teacher_dismiss"
        )
        student_headers, student_info = await _get_auth_headers(
            client, role="student", name_prefix="student_dismiss"
        )

        prob_res = await client.get("/api/v1/problems", headers=student_headers)
        problem = prob_res.json()[0]

        async with get_session_factory()() as session:
            sub = Submission(
                user_id=uuid.UUID(student_info["id"]),
                problem_id=uuid.UUID(problem["id"]),
                code="x = 10\n",
                language="python",
                status=SubmissionStatus.COMPLETED,
                verdict=SubmissionVerdict.WRONG_ANSWER,
                runtime_ms=10,
                memory_kb=1024,
                test_cases_passed=0,
                total_test_cases=3,
            )
            session.add(sub)
            await session.commit()
            await session.refresh(sub)

            task = AnnotationTask(
                submission_id=sub.id,
                diagnosis_id=None,
                status=AnnotationTaskStatus.PENDING,
                original_misconception_code="S2",
                original_confidence=0.20,
                trigger_reason="LOW_CONFIDENCE (0.20 < 0.50)",
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            task_id = str(task.id)

        # Dismiss task
        dismiss_res = await client.post(
            f"/api/v1/annotations/{task_id}/dismiss?notes=Student+abandoned+attempt",
            headers=teacher_headers,
        )
        assert dismiss_res.status_code == 200
        dismissed_data = dismiss_res.json()
        assert dismissed_data["status"] == "DISMISSED"
        assert dismissed_data["annotator_notes"] == "Student abandoned attempt"
        assert dismissed_data["assigned_annotator_id"] == teacher_info["id"]


@pytest.mark.asyncio
async def test_resolve_invalid_taxonomy_code() -> None:
    """Verify that resolving with an invalid taxonomy code returns HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        teacher_headers, _ = await _get_auth_headers(
            client, role="teacher", name_prefix="teacher_invalid_tax"
        )
        student_headers, student_info = await _get_auth_headers(
            client, role="student", name_prefix="student_invalid_tax"
        )

        prob_res = await client.get("/api/v1/problems", headers=student_headers)
        problem = prob_res.json()[0]

        async with get_session_factory()() as session:
            sub = Submission(
                user_id=uuid.UUID(student_info["id"]),
                problem_id=uuid.UUID(problem["id"]),
                code="pass\n",
                language="python",
                status=SubmissionStatus.COMPLETED,
                verdict=SubmissionVerdict.WRONG_ANSWER,
                runtime_ms=5,
                memory_kb=512,
                test_cases_passed=0,
                total_test_cases=3,
            )
            session.add(sub)
            await session.commit()
            await session.refresh(sub)

            task = AnnotationTask(
                submission_id=sub.id,
                diagnosis_id=None,
                status=AnnotationTaskStatus.PENDING,
                original_misconception_code="S2",
                original_confidence=0.10,
                trigger_reason="LOW_CONFIDENCE (0.10 < 0.50)",
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            task_id = str(task.id)

        res = await client.post(
            f"/api/v1/annotations/{task_id}/resolve",
            json={"resolved_misconception_code": "Z99"},
            headers=teacher_headers,
        )
        assert res.status_code == 400
        assert "Unknown misconception taxonomy code" in res.json()["detail"]
