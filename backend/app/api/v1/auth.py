"""Authentication and RBAC API routes for CodeRazz."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.config import get_settings
from backend.app.core.dependencies import get_current_user, require_role
from backend.app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from backend.app.database import get_db
from backend.app.models.token import RefreshToken
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RoleUpdateRequest,
    TokenResponse,
    UserProfileResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new student or teacher account",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Register a new student or teacher. Prevents self-assigning privileged roles."""
    # Check duplicate email
    query = select(User).where(User.email == payload.email.lower().strip())
    existing = await db.execute(query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # Hash password with Argon2
    hashed_pwd = hash_password(payload.password)

    new_user = User(
        email=payload.email.lower().strip(),
        hashed_password=hashed_pwd,
        full_name=payload.full_name.strip(),
        role=payload.role,
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserProfileResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive access and refresh tokens",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate credentials and generate JWT access token with a rotating refresh token."""
    query = select(User).where(User.email == payload.email.lower().strip())
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact an administrator.",
        )

    settings = get_settings()

    # Generate tokens
    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
    )
    raw_refresh_token, token_hash, expires_at = generate_refresh_token()

    # Persist hashed refresh token
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(refresh_record)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserProfileResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange refresh token for a new access token",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validate refresh token, rotate token, and issue fresh access token."""
    token_hash = hash_token(payload.refresh_token)
    now = datetime.now(timezone.utc)

    query = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked.is_(False),
    )
    result = await db.execute(query)
    token_record = result.scalar_one_or_none()

    if not token_record or token_record.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid, expired, or revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch corresponding user
    user_query = select(User).where(User.id == token_record.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found.",
        )

    # Rotate refresh token: revoke current, issue new
    token_record.revoked = True

    settings = get_settings()
    new_access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
    )
    new_raw_refresh, new_token_hash, new_expires_at = generate_refresh_token()

    new_record = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=new_expires_at,
        revoked=False,
    )
    db.add(new_record)
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_raw_refresh,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserProfileResponse.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke session refresh tokens",
)
async def logout(
    payload: Optional[RefreshTokenRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Revoke specific refresh token or all user tokens on logout."""
    if payload and payload.refresh_token:
        # Revoke single session
        t_hash = hash_token(payload.refresh_token)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.token_hash == t_hash,
            )
            .values(revoked=True)
        )
    else:
        # Revoke all sessions for user
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == current_user.id)
            .values(revoked=True)
        )

    await db.execute(stmt)
    await db.commit()
    return MessageResponse(message="Successfully logged out and session revoked.")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Retrieve current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Return profile details of the currently authenticated user."""
    return UserProfileResponse.model_validate(current_user)


# ---------------------------------------------------------------------------
# RBAC Verification / Probe Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/role-test/student",
    response_model=MessageResponse,
    summary="Verify STUDENT role access",
)
async def test_student_role(
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
) -> MessageResponse:
    return MessageResponse(
        message=(
            f"Access granted to student endpoint for user {current_user.email} "
            f"(Role: {current_user.role.value})"
        )
    )


@router.get(
    "/role-test/teacher",
    response_model=MessageResponse,
    summary="Verify TEACHER role access",
)
async def test_teacher_role(
    current_user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
) -> MessageResponse:
    return MessageResponse(
        message=(
            f"Access granted to teacher endpoint for user {current_user.email} "
            f"(Role: {current_user.role.value})"
        )
    )


@router.get(
    "/role-test/annotator",
    response_model=MessageResponse,
    summary="Verify ANNOTATOR role access",
)
async def test_annotator_role(
    current_user: User = Depends(require_role(UserRole.ANNOTATOR, UserRole.ADMIN)),
) -> MessageResponse:
    return MessageResponse(
        message=(
            f"Access granted to annotator endpoint for user {current_user.email} "
            f"(Role: {current_user.role.value})"
        )
    )


@router.get(
    "/role-test/admin",
    response_model=MessageResponse,
    summary="Verify ADMIN role access",
)
async def test_admin_role(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> MessageResponse:
    return MessageResponse(
        message=(
            f"Access granted to admin endpoint for user {current_user.email} "
            f"(Role: {current_user.role.value})"
        )
    )


@router.put(
    "/users/{user_id}/role",
    response_model=UserProfileResponse,
    summary="Admin-only: Update user role",
)
async def update_user_role(
    user_id: uuid.UUID,
    payload: RoleUpdateRequest,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Allow administrators to promote or demote user roles."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    target_user.role = payload.role
    await db.commit()
    await db.refresh(target_user)

    return UserProfileResponse.model_validate(target_user)

