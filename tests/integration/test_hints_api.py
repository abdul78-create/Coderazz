"""Integration tests for the 5-Tier Progressive Hint Ladder API."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


async def _get_student_headers(client: AsyncClient, name_prefix: str = "student") -> dict[str, str]:
    """Helper to register and login a distinct student user."""
    email = f"{name_prefix}_{uuid.uuid4().hex[:8]}@coderazz.org"
    password = "StudentSecurePass#123"

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"{name_prefix.capitalize()} User",
            "role": "student",
        },
    )
    assert reg_res.status_code == 201, f"Student register failed: {reg_res.text}"

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200, f"Student login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_hint_unlock_sequential_progression_and_retrieval() -> None:
    """Verify progressive sequential unlock of all 5 tiers with leak checks and penalty tracking."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_student_headers(client, "hint_prog")

        # Retrieve problem list
        prob_res = await client.get("/api/v1/problems", headers=headers)
        assert prob_res.status_code == 200
        problems = prob_res.json()
        assert len(problems) > 0
        problem = problems[0]

        # Submit code with off-by-one misconception (A1)
        broken_code = (
            "import sys\n"
            "def solve():\n"
            "    arr = [1, 2, 3]\n"
            "    for i in range(len(arr) + 1):\n"
            "        x = arr[i]\n"
            "solve()\n"
        )
        sub_res = await client.post(
            "/api/v1/submissions",
            json={
                "problem_id": problem["id"],
                "code": broken_code,
                "language": "python",
            },
            headers=headers,
        )
        assert sub_res.status_code == 201
        sub_data = sub_res.json()
        submission_id = sub_data["id"]

        # Level 1: Nudge
        h1_res = await client.post(
            f"/api/v1/submissions/{submission_id}/hints",
            json={"desired_level": 1},
            headers=headers,
        )
        assert h1_res.status_code == 201
        h1 = h1_res.json()
        assert h1["hint_level"] == 1
        assert h1["hint_tier_name"] == "Level 1: Nudge"
        assert h1["penalty_score"] == 0.0
        assert h1["leak_check_passed"] is True
        assert len(h1["hint_content"]) > 10

        # Level 2: Conceptual Explanation
        h2_res = await client.post(
            f"/api/v1/submissions/{submission_id}/hints",
            headers=headers,  # Omit body: auto-infers next level
        )
        assert h2_res.status_code == 201
        h2 = h2_res.json()
        assert h2["hint_level"] == 2
        assert h2["hint_tier_name"] == "Level 2: Conceptual Explanation"
        assert h2["penalty_score"] == 0.05
        assert h2["leak_check_passed"] is True

        # Attempt to skip Level 3 and request Level 4 -> must be rejected
        skip_res = await client.post(
            f"/api/v1/submissions/{submission_id}/hints",
            json={"desired_level": 4},
            headers=headers,
        )
        assert skip_res.status_code == 400
        assert "sequential" in skip_res.json()["detail"].lower()

        # Unlock Level 3: Counter-Example
        h3_res = await client.post(
            f"/api/v1/submissions/{submission_id}/hints",
            json={"desired_level": 3},
            headers=headers,
        )
        assert h3_res.status_code == 201
        h3 = h3_res.json()
        assert h3["hint_level"] == 3
        assert h3["penalty_score"] == 0.10

        # Unlock Level 4: Worked Analogue
        h4_res = await client.post(
            f"/api/v1/submissions/{submission_id}/hints",
            headers=headers,
        )
        assert h4_res.status_code == 201
        h4 = h4_res.json()
        assert h4["hint_level"] == 4
        assert h4["penalty_score"] == 0.15

        # Unlock Level 5: Targeted Pointer
        h5_res = await client.post(
            f"/api/v1/submissions/{submission_id}/hints",
            headers=headers,
        )
        assert h5_res.status_code == 201
        h5 = h5_res.json()
        assert h5["hint_level"] == 5
        assert h5["penalty_score"] == 0.25

        # Attempt to unlock Level 6 -> should fail
        cap_res = await client.post(
            f"/api/v1/submissions/{submission_id}/hints",
            headers=headers,
        )
        assert cap_res.status_code == 400
        assert (
            "all 5 progressive hint levels have already been unlocked"
            in cap_res.json()["detail"].lower()
        )

        # Retrieve unlocked hints list
        list_res = await client.get(
            f"/api/v1/submissions/{submission_id}/hints",
            headers=headers,
        )
        assert list_res.status_code == 200
        hint_list = list_res.json()
        assert hint_list["submission_id"] == submission_id
        assert len(hint_list["hints"]) == 5
        assert hint_list["max_unlocked_level"] == 5
        assert hint_list["total_penalty"] == 0.55


@pytest.mark.asyncio
async def test_hint_unlock_rbac_cross_student_forbidden() -> None:
    """A student must NOT be able to view or unlock hints on another student's submission."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers1 = await _get_student_headers(client, "student_one")
        headers2 = await _get_student_headers(client, "student_two")

        # Student 1 gets problem and submits code
        prob_res = await client.get("/api/v1/problems", headers=headers1)
        problem = prob_res.json()[0]

        sub_res = await client.post(
            "/api/v1/submissions",
            json={
                "problem_id": problem["id"],
                "code": "def solve():\n    return 42\n",
                "language": "python",
            },
            headers=headers1,
        )
        submission_id = sub_res.json()["id"]

        # Student 2 attempts to unlock hint on Student 1's submission
        unlock_res = await client.post(
            f"/api/v1/submissions/{submission_id}/hints",
            headers=headers2,
        )
        assert unlock_res.status_code == 403
        assert "not authorized" in unlock_res.json()["detail"].lower()

        # Student 2 attempts to view hints on Student 1's submission
        view_res = await client.get(
            f"/api/v1/submissions/{submission_id}/hints",
            headers=headers2,
        )
        assert view_res.status_code == 403


@pytest.mark.asyncio
async def test_hint_unlock_nonexistent_submission() -> None:
    """Requesting hints for a nonexistent submission returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_student_headers(client, "hint_missing")
        fake_id = uuid.uuid4()
        res = await client.post(
            f"/api/v1/submissions/{fake_id}/hints",
            headers=headers,
        )
        assert res.status_code == 404
