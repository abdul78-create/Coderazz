"""CLI utility to create or verify the primary administrator account."""

import asyncio
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import re

from sqlalchemy import select

from backend.app.config import get_settings
from backend.app.core.security import hash_password
from backend.app.database import get_engine, get_session_factory
from backend.app.models.user import User, UserRole


async def bootstrap_admin(
    email: str | None = None, password: str | None = None, force: bool = False
):
    """Ensure at least one administrator exists on the platform safely."""
    settings = get_settings()
    admin_email = (email or settings.ADMIN_INITIAL_EMAIL).lower().strip()
    admin_pwd = password or settings.ADMIN_INITIAL_PASSWORD

    # Safeguard 1: Block default development credentials in production
    if settings.ENV == "production" and admin_pwd == "AdminInitial#2026":
        raise ValueError(
            "CRITICAL SECURITY BLOCK: Cannot bootstrap administrator with default development password "
            "in production environment. Provide a secure, unique password."
        )

    # Safeguard 2: Password complexity check
    if len(admin_pwd) < 8 or not re.search(r"[A-Za-z]", admin_pwd) or not re.search(r"\d", admin_pwd):
        raise ValueError(
            "Administrator password must be at least 8 characters long and contain both letters and digits."
        )

    print(f"Checking administrator account for: {admin_email}...")
    factory = get_session_factory()

    async with factory() as session:
        # Check if the specific admin email exists
        query = select(User).where(User.email == admin_email)
        result = await session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.role != UserRole.ADMIN:
                existing.role = UserRole.ADMIN
                await session.commit()
                print(f"User {admin_email} promoted to ADMIN.")
            else:
                print(f"Administrator {admin_email} already exists and is active.")
            return

        # Safeguard 3: Prevent accidental proliferation of uncontrolled administrators
        admin_count_query = select(User).where(User.role == UserRole.ADMIN)
        admin_count_res = await session.execute(admin_count_query)
        existing_admins = admin_count_res.scalars().all()

        if existing_admins and not force:
            print(
                f"WARNING: Platform already has {len(existing_admins)} active administrator(s): "
                f"{[a.email for a in existing_admins]}. "
                "To bootstrap an additional administrator, pass '--force'."
            )
            return

        # Create new primary administrator
        new_admin = User(
            email=admin_email,
            hashed_password=hash_password(admin_pwd),
            full_name="Platform Administrator",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        session.add(new_admin)
        await session.commit()
        print(f"Successfully created primary administrator: {admin_email}")

    engine = get_engine()
    await engine.dispose()


if __name__ == "__main__":
    email_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
    pwd_arg = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    force_arg = "--force" in sys.argv
    asyncio.run(bootstrap_admin(email_arg, pwd_arg, force_arg))
