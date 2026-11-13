"""Integration tests for Class Groups, Join Codes, and Roster RBAC isolation."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


async def _get_user_headers(
    client: AsyncClient,
    role: str = "student",
    name_prefix: str = "user",
) -> tuple[dict[str, str], dict]:
    """Register and login a user, returning auth headers and profile dict."""
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
async def test_teacher_class_creation_and_listing() -> None:
    """A teacher can create a class group, receive a join code, and list their classes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        teacher_headers, teacher = await _get_user_headers(client, role="teacher", name_prefix="prof_smith")

        create_res = await client.post(
            "/api/v1/classes",
            json={
                "name": "CS101: Intro to Python",
                "description": "Foundational Python syntax, control flow, and data structures.",
            },
            headers=teacher_headers,
        )
        assert create_res.status_code == 201
        cls_data = create_res.json()
        assert cls_data["name"] == "CS101: Intro to Python"
        assert len(cls_data["join_code"]) == 6
        assert cls_data["teacher_id"] == teacher["id"]
        assert cls_data["student_count"] == 0

        # Teacher lists their classes
        list_res = await client.get("/api/v1/classes", headers=teacher_headers)
        assert list_res.status_code == 200
        classes = list_res.json()
        assert len(classes) >= 1
        found = next((c for c in classes if c["id"] == cls_data["id"]), None)
        assert found is not None
        assert found["join_code"] == cls_data["join_code"]


@pytest.mark.asyncio
async def test_student_join_code_enrollment_and_duplicate_prevention() -> None:
    """Student can join a class using join code, but cannot double-enroll or use invalid codes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        teacher_headers, _ = await _get_user_headers(client, role="teacher", name_prefix="prof_adams")
        student_headers, student = await _get_user_headers(client, role="student", name_prefix="alice")

        # Teacher creates class
        create_res = await client.post(
            "/api/v1/classes",
            json={"name": "Data Structures Fall 2026"},
            headers=teacher_headers,
        )
        cls_data = create_res.json()
        join_code = cls_data["join_code"]

        # Student joins with valid join code
        join_res = await client.post(
            "/api/v1/classes/join",
            json={"join_code": join_code},
            headers=student_headers,
        )
        assert join_res.status_code == 201
        enr_data = join_res.json()
        assert enr_data["class_id"] == cls_data["id"]
        assert enr_data["student_id"] == student["id"]
        assert enr_data["class_name"] == "Data Structures Fall 2026"

        # Attempt to join again -> 400 Bad Request
        dup_res = await client.post(
            "/api/v1/classes/join",
            json={"join_code": join_code},
            headers=student_headers,
        )
        assert dup_res.status_code == 400
        assert "already enrolled" in dup_res.json()["detail"].lower()

        # Attempt to join with invalid code -> 404
        fake_res = await client.post(
            "/api/v1/classes/join",
            json={"join_code": "INVALID99"},
            headers=student_headers,
        )
        assert fake_res.status_code == 404

        # Student lists their enrolled classes
        student_list_res = await client.get("/api/v1/classes", headers=student_headers)
        assert student_list_res.status_code == 200
        student_classes = student_list_res.json()
        assert any(c["id"] == cls_data["id"] for c in student_classes)


@pytest.mark.asyncio
async def test_class_roster_rbac_isolation() -> None:
    """Enforce strict isolation: non-enrolled students cannot view class; students cannot view roster; other teachers cannot view foreign rosters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        t1_headers, _ = await _get_user_headers(client, role="teacher", name_prefix="prof_one")
        t2_headers, _ = await _get_user_headers(client, role="teacher", name_prefix="prof_two")
        s1_headers, _ = await _get_user_headers(client, role="student", name_prefix="enrolled_bob")
        s2_headers, _ = await _get_user_headers(client, role="student", name_prefix="outsider_charlie")

        # Teacher 1 creates Class 1
        create_res = await client.post(
            "/api/v1/classes",
            json={"name": "Algorithms Section A"},
            headers=t1_headers,
        )
        cls_id = create_res.json()["id"]
        join_code = create_res.json()["join_code"]

        # Student 1 enrolls
        await client.post(
            "/api/v1/classes/join",
            json={"join_code": join_code},
            headers=s1_headers,
        )

        # 1. Non-enrolled Student 2 tries to GET class details -> 403 Forbidden
        outsider_view = await client.get(f"/api/v1/classes/{cls_id}", headers=s2_headers)
        assert outsider_view.status_code == 403

        # 2. Enrolled Student 1 CAN GET class details -> 200 OK
        enrolled_view = await client.get(f"/api/v1/classes/{cls_id}", headers=s1_headers)
        assert enrolled_view.status_code == 200
        assert enrolled_view.json()["name"] == "Algorithms Section A"

        # 3. Student 1 tries to GET class roster -> 403 Forbidden
        roster_student_view = await client.get(f"/api/v1/classes/{cls_id}/roster", headers=s1_headers)
        assert roster_student_view.status_code == 403

        # 4. Teacher 2 (different teacher) tries to GET Teacher 1's roster -> 403 Forbidden
        foreign_teacher_view = await client.get(f"/api/v1/classes/{cls_id}/roster", headers=t2_headers)
        assert foreign_teacher_view.status_code == 403

        # 5. Teacher 1 (owner) GETs roster -> 200 OK, sees Student 1
        owner_roster = await client.get(f"/api/v1/classes/{cls_id}/roster", headers=t1_headers)
        assert owner_roster.status_code == 200
        roster_data = owner_roster.json()
        assert len(roster_data["students"]) == 1
        assert "bob" in roster_data["students"][0]["full_name"].lower()
