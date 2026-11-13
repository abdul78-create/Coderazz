"""Integration tests verifying end-to-end misconception diagnosis in submissions API."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.models.submission import SubmissionVerdict


async def _get_student_headers(client: AsyncClient) -> dict[str, str]:
    """Helper to register and login a student, returning Authorization headers."""
    email = f"diag_student_{uuid.uuid4().hex[:8]}@coderazz.org"
    password = "StudentPass#123"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Diagnosis Student", "role": "student"},
    )
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_run_code_attaches_diagnosis_on_failure() -> None:
    """POST /api/v1/submissions/run with broken code should return diagnosis."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_student_headers(client)

        # Code with off-by-one error (A1)
        faulty_code = (
            "import sys\n"
            "def solve():\n"
            "    arr = [1, 2, 3]\n"
            "    for i in range(len(arr) + 1):\n"
            "        x = arr[i]\n"
            "solve()\n"
        )

        res = await client.post(
            "/api/v1/submissions/run",
            json={"code": faulty_code, "custom_input": "test\n"},
            headers=headers,
        )

        assert res.status_code == 200
        data = res.json()
        assert data["verdict"] != SubmissionVerdict.ACCEPTED
        assert data["diagnosis"] is not None
        diag = data["diagnosis"]
        assert diag["misconception_code"] == "A1"
        assert diag["confidence_score"] >= 0.90
        assert diag["detector_type"] == "rule_ast"
        assert 4 in diag["evidence_lines"]
        assert "off-by-one" in diag["explanation"].lower()


@pytest.mark.asyncio
async def test_submit_code_persists_diagnosis_in_database() -> None:
    """POST /api/v1/submissions with failing code saves diagnosis row and GET returns it."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_student_headers(client)

        # Get problems
        prob_res = await client.get("/api/v1/problems", headers=headers)
        problems = prob_res.json()
        assert len(problems) > 0
        target_problem = problems[0]

        # Submit code with syntax error (S1)
        syntax_broken_code = "def solve(\n    broken syntax\n"

        sub_res = await client.post(
            "/api/v1/submissions",
            json={
                "problem_id": target_problem["id"],
                "code": syntax_broken_code,
                "language": "python",
            },
            headers=headers,
        )

        assert sub_res.status_code == 201
        data = sub_res.json()
        assert data["verdict"] in (SubmissionVerdict.RUNTIME_ERROR, SubmissionVerdict.COMPILATION_ERROR)
        assert data["diagnosis"] is not None
        assert data["diagnosis"]["misconception_code"] == "S1"
        assert data["diagnosis"]["confidence_score"] == 1.0

        submission_id = data["id"]

        # Fetch submission via GET /api/v1/submissions/{id}
        get_res = await client.get(f"/api/v1/submissions/{submission_id}", headers=headers)
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == submission_id
        assert get_data["diagnosis"] is not None
        assert get_data["diagnosis"]["misconception_code"] == "S1"
        assert len(get_data["diagnoses"]) >= 1
