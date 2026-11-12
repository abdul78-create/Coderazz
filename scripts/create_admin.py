"""CLI utility to create or verify the primary administrator account."""

import asyncio
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from backend.app.config import get_settings
from backend.app.core.security import hash_password
from backend.app.database import get_engine, get_session_factory
from backend.app.models.user import User, UserRole


async def bootstrap_admin(email: str | None = None, password: str | None = None):
    """Ensure at least one administrator exists on the platform."""
    settings = get_settings()
    admin_email = (email or settings.ADMIN_INITIAL_EMAIL).lower().strip()
    admin_pwd = password or settings.ADMIN_INITIAL_PASSWORD

    print(f"Checking administrator account for: {admin_email}...")
    factory = get_session_factory()

    async with factory() as session:
        # Check if any admin exists
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

        # Create new admin
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
    email_arg = sys.argv[1] if len(sys.argv) > 1 else None
    pwd_arg = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(bootstrap_admin(email_arg, pwd_arg))
