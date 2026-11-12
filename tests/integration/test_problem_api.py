"""Integration tests for CodeRazz Problem Catalog & Management APIs."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


async def _get_auth_headers(client: AsyncClient, email: str, password: str, role: str) -> dict[str, str]:
    """Helper to register and login a user, returning Authorization headers."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": f"User {role}", "role": role},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_problem_listing():
    """Verify listing problems returns seeded problems with case counts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/problems")
        assert res.status_code == 200
        problems = res.json()
        assert len(problems) >= 5

        slugs = [p["slug"] for p in problems]
        assert "two-sum" in slugs
        assert "reverse-string" in slugs
        assert "count-vowels" in slugs
        assert "fizz-buzz" in slugs
        assert "valid-palindrome" in slugs

        # Verify problem summary fields
        for p in problems:
            assert "id" in p
            assert "slug" in p
            assert "title" in p
            assert "difficulty" in p
            assert "sample_cases_count" in p
            assert "total_cases_count" in p
            assert p["total_cases_count"] >= p["sample_cases_count"]


@pytest.mark.asyncio
async def test_problem_listing_filter_by_difficulty():
    """Verify problems can be filtered by difficulty level."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_easy = await client.get("/api/v1/problems?difficulty=EASY")
        assert res_easy.status_code == 200
        easy_problems = res_easy.json()
        assert len(easy_problems) >= 5
        for p in easy_problems:
            assert p["difficulty"] == "EASY"

        res_hard = await client.get("/api/v1/problems?difficulty=HARD")
        assert res_hard.status_code == 200
        hard_problems = res_hard.json()
        assert isinstance(hard_problems, list)


@pytest.mark.asyncio
async def test_problem_detail_and_hidden_case_masking():
    """CRITICAL: Problem detail must expose ONLY sample test cases; hidden cases must NEVER leak."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/problems/two-sum")
        assert res.status_code == 200
        prob = res.json()

        assert prob["slug"] == "two-sum"
        assert prob["title"] == "Two Sum"
        assert "def solve" in prob["starter_code"]
        assert prob["time_limit_ms"] > 0
        assert prob["memory_limit_mb"] > 0

        # Verify test cases: sample_test_cases contains only public samples
        sample_cases = prob["sample_test_cases"]
        assert len(sample_cases) == 2  # Two Sum has 2 samples seeded
        for tc in sample_cases:
            assert "input_data" in tc
            assert "expected_output" in tc
            # is_hidden should NOT even be in the public response schema
            assert "is_hidden" not in tc


@pytest.mark.asyncio
async def test_problem_detail_by_uuid():
    """Verify problem can be retrieved by UUID primary key as well as slug."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get problem list to find UUID
        res_list = await client.get("/api/v1/problems")
        first_prob = res_list.json()[0]
        prob_id = first_prob["id"]

        res_detail = await client.get(f"/api/v1/problems/{prob_id}")
        assert res_detail.status_code == 200
        assert res_detail.json()["id"] == prob_id
        assert res_detail.json()["slug"] == first_prob["slug"]


@pytest.mark.asyncio
async def test_problem_not_found():
    """Verify 404 is returned for non-existent slug or ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/problems/non-existent-problem-slug-xyz")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_problem_creation_rbac():
    """Verify only admin/teacher can create problems; students and anonymous users are blocked."""
    transport = ASGITransport(app=app)
    new_slug = f"prob-{uuid.uuid4().hex[:6]}"
    problem_payload = {
        "title": "Custom Test Problem",
        "slug": new_slug,
        "difficulty": "EASY",
        "description": "Calculate sum of two numbers.",
        "starter_code": "def add(a: int, b: int) -> int:\n    pass\n",
        "category": "Math",
        "test_cases": [
            {"input_data": "1 2", "expected_output": "3", "is_hidden": False, "explanation": "1 + 2 = 3"},
            {"input_data": "10 20", "expected_output": "30", "is_hidden": True},
        ],
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Anonymous -> 401 Unauthorized
        anon_res = await client.post("/api/v1/problems", json=problem_payload)
        assert anon_res.status_code == 401

        # 2. Student -> 403 Forbidden
        student_headers = await _get_auth_headers(
            client, f"stud_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        student_res = await client.post("/api/v1/problems", json=problem_payload, headers=student_headers)
        assert student_res.status_code == 403

        # 3. Admin -> 201 Created
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@coderazz.edu", "password": "AdminInitial#2026"},
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        admin_res = await client.post("/api/v1/problems", json=problem_payload, headers=admin_headers)
        assert admin_res.status_code == 201
        created = admin_res.json()
        assert created["slug"] == new_slug
        assert created["title"] == "Custom Test Problem"

        # Verify created problem can be retrieved
        fetch_res = await client.get(f"/api/v1/problems/{new_slug}")
        assert fetch_res.status_code == 200
        # Only 1 sample test case returned (hidden one is masked)
        assert len(fetch_res.json()["sample_test_cases"]) == 1
        assert fetch_res.json()["sample_test_cases"][0]["input_data"] == "1 2"
