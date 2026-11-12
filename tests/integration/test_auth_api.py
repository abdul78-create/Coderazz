"""Integration tests for CodeRazz Authentication & RBAC APIs."""

import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.security import create_access_token
from backend.app.main import app


@pytest.mark.asyncio
async def test_student_and_teacher_registration():
    """Verify students and teachers can register successfully with valid credentials."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register student
        student_email = f"student_{uuid.uuid4().hex[:8]}@coderazz.edu"
        res_student = await client.post(
            "/api/v1/auth/register",
            json={
                "email": student_email,
                "password": "StudentPass#123",
                "full_name": "Test Student",
                "role": "student",
            },
        )
        assert res_student.status_code == 201
        data = res_student.json()
        assert data["email"] == student_email
        assert data["role"] == "student"
        assert "hashed_password" not in data  # Never expose password hash

        # 2. Register teacher
        teacher_email = f"teacher_{uuid.uuid4().hex[:8]}@coderazz.edu"
        res_teacher = await client.post(
            "/api/v1/auth/register",
            json={
                "email": teacher_email,
                "password": "TeacherPass#123",
                "full_name": "Test Teacher",
                "role": "teacher",
            },
        )
        assert res_teacher.status_code == 201
        assert res_teacher.json()["role"] == "teacher"


@pytest.mark.asyncio
async def test_duplicate_registration_rejected():
    """Verify duplicate email registration returns 409 Conflict."""
    transport = ASGITransport(app=app)
    email = f"dup_{uuid.uuid4().hex[:8]}@coderazz.edu"
    payload = {
        "email": email,
        "password": "ValidPassword#1",
        "full_name": "Duplicate User",
        "role": "student",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res1 = await client.post("/api/v1/auth/register", json=payload)
        assert res1.status_code == 201

        res2 = await client.post("/api/v1/auth/register", json=payload)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_privilege_escalation_on_registration_rejected():
    """Verify attempting to self-register as ADMIN or ANNOTATOR is strictly rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempt to register as admin
        res_admin = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"hacker_admin_{uuid.uuid4().hex[:8]}@test.com",
                "password": "HackerPass#123",
                "full_name": "Hacker",
                "role": "admin",
            },
        )
        assert res_admin.status_code == 422
        assert "privilege escalation prevented" in str(res_admin.json()).lower()

        # Attempt to register as annotator
        res_annotator = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"hacker_annotator_{uuid.uuid4().hex[:8]}@test.com",
                "password": "HackerPass#123",
                "full_name": "Hacker",
                "role": "annotator",
            },
        )
        assert res_annotator.status_code == 422


@pytest.mark.asyncio
async def test_login_flow_and_credential_validation():
    """Verify login handles valid credentials, wrong passwords, and nonexistent users."""
    transport = ASGITransport(app=app)
    email = f"auth_test_{uuid.uuid4().hex[:8]}@coderazz.edu"
    password = "CorrectPassword#123"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Auth Tester",
                "role": "student",
            },
        )
        assert reg_res.status_code == 201

        # 1. Successful login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["user"]["email"] == email

        # 2. Incorrect password rejected
        bad_pwd_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword#999"},
        )
        assert bad_pwd_res.status_code == 401

        # 3. Nonexistent email rejected
        no_user_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent_email_123@coderazz.edu", "password": password},
        )
        assert no_user_res.status_code == 401


@pytest.mark.asyncio
async def test_user_profile_me_endpoint():
    """Verify /api/v1/auth/me returns profile with valid token and rejects invalid tokens."""
    transport = ASGITransport(app=app)
    email = f"me_test_{uuid.uuid4().hex[:8]}@coderazz.edu"
    password = "ValidPassword#123"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Me User", "role": "student"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        token = login.json()["access_token"]
        user_id = login.json()["user"]["id"]

        # Valid request
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        assert me_res.json()["email"] == email

        # Unauthenticated request (no token)
        unauth_res = await client.get("/api/v1/auth/me")
        assert unauth_res.status_code == 401

        # Expired token request
        expired_token = create_access_token(
            subject=user_id,
            role="student",
            expires_delta=timedelta(seconds=-10),
        )
        exp_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert exp_res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation():
    """Verify refresh token rotation and rejection of revoked tokens."""
    transport = ASGITransport(app=app)
    email = f"refresh_{uuid.uuid4().hex[:8]}@coderazz.edu"
    password = "RefreshPassword#123"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Refresher", "role": "student"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        old_refresh_token = login.json()["refresh_token"]

        # 1. Exchange refresh token for new access and refresh tokens
        refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert refresh_res.status_code == 200
        new_data = refresh_res.json()
        new_access_token = new_data["access_token"]
        new_refresh_token = new_data["refresh_token"]

        assert new_refresh_token != old_refresh_token

        # Verify new access token works
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_res.status_code == 200

        # 2. Reusing the old refresh token must fail (Token Rotation)
        reused_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert reused_res.status_code == 401

        # 3. Logout revokes token
        logout_res = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_access_token}"},
            json={"refresh_token": new_refresh_token},
        )
        assert logout_res.status_code == 200

        # Subsequent refresh with revoked token fails
        post_logout_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh_token},
        )
        assert post_logout_refresh.status_code == 401


@pytest.mark.asyncio
async def test_rbac_permission_matrix():
    """Verify role-based access control enforces permissions on student, teacher, annotator, admin."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create student and teacher
        s_email = f"student_rbac_{uuid.uuid4().hex[:8]}@coderazz.edu"
        t_email = f"teacher_rbac_{uuid.uuid4().hex[:8]}@coderazz.edu"
        pwd = "ComplexPassword#123"

        await client.post(
            "/api/v1/auth/register",
            json={"email": s_email, "password": pwd, "full_name": "Student", "role": "student"},
        )
        await client.post(
            "/api/v1/auth/register",
            json={"email": t_email, "password": pwd, "full_name": "Teacher", "role": "teacher"},
        )

        s_login = await client.post("/api/v1/auth/login", json={"email": s_email, "password": pwd})
        s_token = s_login.json()["access_token"]

        t_login = await client.post("/api/v1/auth/login", json={"email": t_email, "password": pwd})
        t_token = t_login.json()["access_token"]

        # Student testing
        # Can access student endpoint
        res = await client.get("/api/v1/auth/role-test/student", headers={"Authorization": f"Bearer {s_token}"})
        assert res.status_code == 200

        # CANNOT access teacher endpoint
        res = await client.get("/api/v1/auth/role-test/teacher", headers={"Authorization": f"Bearer {s_token}"})
        assert res.status_code == 403

        # CANNOT access admin endpoint
        res = await client.get("/api/v1/auth/role-test/admin", headers={"Authorization": f"Bearer {s_token}"})
        assert res.status_code == 403

        # Teacher testing
        # Can access teacher endpoint
        res = await client.get("/api/v1/auth/role-test/teacher", headers={"Authorization": f"Bearer {t_token}"})
        assert res.status_code == 200

        # Teacher CANNOT access admin endpoint
        res = await client.get("/api/v1/auth/role-test/admin", headers={"Authorization": f"Bearer {t_token}"})
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_role_management():
    """Verify admin login, access to all endpoints, and role update capability."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login with bootstrapped admin credentials
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@coderazz.edu", "password": "AdminInitial#2026"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]

        # Admin can access all role probe endpoints
        assert (await client.get("/api/v1/auth/role-test/admin", headers={"Authorization": f"Bearer {admin_token}"})).status_code == 200
        assert (await client.get("/api/v1/auth/role-test/teacher", headers={"Authorization": f"Bearer {admin_token}"})).status_code == 200
        assert (await client.get("/api/v1/auth/role-test/student", headers={"Authorization": f"Bearer {admin_token}"})).status_code == 200
        assert (await client.get("/api/v1/auth/role-test/annotator", headers={"Authorization": f"Bearer {admin_token}"})).status_code == 200

        # Register a regular student
        s_email = f"promote_{uuid.uuid4().hex[:8]}@coderazz.edu"
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": s_email, "password": "Password#123", "full_name": "To Promote", "role": "student"},
        )
        user_id = reg.json()["id"]

        # Non-admin cannot promote user
        s_login = await client.post("/api/v1/auth/login", json={"email": s_email, "password": "Password#123"})
        s_token = s_login.json()["access_token"]
        unauth_promote = await client.put(
            f"/api/v1/auth/users/{user_id}/role",
            headers={"Authorization": f"Bearer {s_token}"},
            json={"role": "annotator"},
        )
        assert unauth_promote.status_code == 403

        # Admin can promote user to ANNOTATOR
        promote_res = await client.put(
            f"/api/v1/auth/users/{user_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "annotator"},
        )
        assert promote_res.status_code == 200
        assert promote_res.json()["role"] == "annotator"


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection_invalidates_all_sessions():
    """Verify RFC 6749 Section 4.14.2: Token reuse invalidates entire token family."""
    transport = ASGITransport(app=app)
    email = f"reuse_{uuid.uuid4().hex[:8]}@coderazz.edu"
    password = "ReusePassword#123"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Reuse Victim", "role": "student"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        token_1 = login.json()["refresh_token"]

        # Legitimate rotation: exchange token_1 for token_2
        refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token_1},
        )
        assert refresh_res.status_code == 200
        token_2 = refresh_res.json()["refresh_token"]

        # MALICIOUS REUSE: An attacker presents already-consumed token_1
        reuse_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token_1},
        )
        assert reuse_res.status_code == 401
        assert "reuse detected" in reuse_res.json()["detail"].lower()

        # Legitimate token_2 MUST now be invalidated as part of compromised token family
        compromised_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": token_2},
        )
        assert compromised_res.status_code == 401


