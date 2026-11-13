"""Integration tests for Teacher Analytics & Struggle Trends API endpoints."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


async def _get_user_headers(
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
async def test_class_misconception_aggregation_and_proportions() -> None:
    """Verify class-wide aggregation of misconception frequency, student counts, and percentages."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        teacher_headers, _ = await _get_user_headers(client, role="teacher", name_prefix="prof_turing")
        s1_headers, _ = await _get_user_headers(client, role="student", name_prefix="student_one")
        s2_headers, _ = await _get_user_headers(client, role="student", name_prefix="student_two")

        # 1. Teacher creates class
        create_res = await client.post(
            "/api/v1/classes",
            json={"name": "CS201 Data Structures"},
            headers=teacher_headers,
        )
        assert create_res.status_code == 201
        cls_data = create_res.json()
        class_id = cls_data["id"]
        join_code = cls_data["join_code"]

        # 2. Both students enroll
        await client.post("/api/v1/classes/join", json={"join_code": join_code}, headers=s1_headers)
        await client.post("/api/v1/classes/join", json={"join_code": join_code}, headers=s2_headers)

        # 3. Retrieve problem
        prob_res = await client.get("/api/v1/problems", headers=s1_headers)
        problem = prob_res.json()[0]

        # Student 1 submits A1 code
        a1_code = (
            "import sys\n"
            "def solve():\n"
            "    arr = [1, 2, 3]\n"
            "    for i in range(len(arr) + 1):\n"
            "        x = arr[i]\n"
            "solve()\n"
        )
        sub1_res = await client.post(
            "/api/v1/submissions",
            json={"problem_id": problem["id"], "code": a1_code, "language": "python"},
            headers=s1_headers,
        )
        assert sub1_res.status_code == 201
        sub1_id = sub1_res.json()["id"]

        # Student 1 unlocks Level 1 hint
        await client.post(f"/api/v1/submissions/{sub1_id}/hints", headers=s1_headers)

        # Student 2 submits A1 code
        sub2_res = await client.post(
            "/api/v1/submissions",
            json={"problem_id": problem["id"], "code": a1_code, "language": "python"},
            headers=s2_headers,
        )
        assert sub2_res.status_code == 201

        # Student 1 also submits S1 code (syntax slip)
        s1_code = "def solve(\n    invalid python syntax\n"
        await client.post(
            "/api/v1/submissions",
            json={"problem_id": problem["id"], "code": s1_code, "language": "python"},
            headers=s1_headers,
        )

        # 4. Teacher requests misconception analytics
        analytics_res = await client.get(
            f"/api/v1/classes/{class_id}/analytics/misconceptions",
            headers=teacher_headers,
        )
        assert analytics_res.status_code == 200
        data = analytics_res.json()
        assert data["class_id"] == class_id
        assert data["total_diagnoses"] >= 3
        assert data["total_students_diagnosed"] == 2

        misconceptions = data["misconceptions"]
        a1_item = next((m for m in misconceptions if m["misconception_code"] == "A1"), None)
        assert a1_item is not None
        assert a1_item["count"] >= 2
        assert a1_item["unique_students"] == 2
        assert a1_item["percentage"] > 0.0
        assert "off-by-one" in a1_item["misconception_name"].lower()

        s1_item = next((m for m in misconceptions if m["misconception_code"] == "S1"), None)
        assert s1_item is not None
        assert s1_item["count"] >= 1


@pytest.mark.asyncio
async def test_class_struggle_trends_time_series() -> None:
    """Verify struggle-trends returns time-series with submissions, active students, and hints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        teacher_headers, _ = await _get_user_headers(client, role="teacher", name_prefix="prof_knuth")
        student_headers, _ = await _get_user_headers(client, role="student", name_prefix="student_active")

        # Create class and join
        create_res = await client.post(
            "/api/v1/classes",
            json={"name": "Trends Class"},
            headers=teacher_headers,
        )
        cls_data = create_res.json()
        class_id = cls_data["id"]
        join_code = cls_data["join_code"]

        await client.post("/api/v1/classes/join", json={"join_code": join_code}, headers=student_headers)

        # Submit code
        prob_res = await client.get("/api/v1/problems", headers=student_headers)
        problem = prob_res.json()[0]

        sub_res = await client.post(
            "/api/v1/submissions",
            json={"problem_id": problem["id"], "code": "def solve(): pass\n", "language": "python"},
            headers=student_headers,
        )
        sub_id = sub_res.json()["id"]

        # Unlock a hint
        await client.post(f"/api/v1/submissions/{sub_id}/hints", headers=student_headers)

        # Teacher queries trends
        trends_res = await client.get(
            f"/api/v1/classes/{class_id}/analytics/struggle-trends?days=7",
            headers=teacher_headers,
        )
        assert trends_res.status_code == 200
        trends_data = trends_res.json()
        assert trends_data["class_id"] == class_id
        assert trends_data["time_window_days"] == 7
        assert trends_data["total_submissions"] >= 1
        assert trends_data["total_hints"] >= 1
        assert len(trends_data["trend"]) >= 1

        day_point = trends_data["trend"][0]
        assert "date" in day_point
        assert day_point["submissions_count"] >= 1
        assert day_point["unique_students_active"] >= 1
        assert day_point["hints_requested_count"] >= 1


@pytest.mark.asyncio
async def test_analytics_rbac_isolation() -> None:
    """Enforce that students and foreign teachers cannot inspect class analytics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        t1_headers, _ = await _get_user_headers(client, role="teacher", name_prefix="teacher_alpha")
        t2_headers, _ = await _get_user_headers(client, role="teacher", name_prefix="teacher_beta")
        student_headers, _ = await _get_user_headers(client, role="student", name_prefix="student_gamma")

        create_res = await client.post(
            "/api/v1/classes",
            json={"name": "Alpha Private Class"},
            headers=t1_headers,
        )
        class_id = create_res.json()["id"]

        # Student tries to access analytics -> 403 Forbidden
        s_res = await client.get(f"/api/v1/classes/{class_id}/analytics/misconceptions", headers=student_headers)
        assert s_res.status_code == 403

        # Foreign teacher tries to access analytics -> 403 Forbidden
        t2_res = await client.get(f"/api/v1/classes/{class_id}/analytics/misconceptions", headers=t2_headers)
        assert t2_res.status_code == 403

        # Nonexistent class -> 404
        fake_id = uuid.uuid4()
        fake_res = await client.get(f"/api/v1/classes/{fake_id}/analytics/misconceptions", headers=t1_headers)
        assert fake_res.status_code == 404
