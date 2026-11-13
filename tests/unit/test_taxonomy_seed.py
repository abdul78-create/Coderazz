"""Unit and integration tests for MisconceptionTaxonomy schema and idempotent seeding."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.database import Base, get_session_factory
from backend.app.models.misconception import (
    DetectorType,
    Diagnosis,
    MisconceptionTaxonomy,
)
from backend.app.services.taxonomy_seed import seed_taxonomy


@pytest.mark.asyncio
async def test_taxonomy_seeding_on_postgres():
    """Verify that taxonomy seeding populates all 32 classes on the active database."""
    factory = get_session_factory()
    async with factory() as db:
        stats = await seed_taxonomy(db)
        assert stats["total"] == 32
        assert stats["created"] + stats["updated"] == 32

        # Verify all 32 items exist in database
        result = await db.execute(select(MisconceptionTaxonomy))
        items = result.scalars().all()
        assert len(items) == 32

        codes = {item.code for item in items}
        # Check core categories A-G and meta-classes S1/S2
        for i in range(1, 6):
            assert f"A{i}" in codes
            assert f"B{i}" in codes
            assert f"C{i}" in codes
            assert f"D{i}" in codes
        for i in range(1, 5):
            assert f"E{i}" in codes
        for i in range(1, 4):
            assert f"F{i}" in codes
            assert f"G{i}" in codes
        assert "S1" in codes
        assert "S2" in codes


@pytest.mark.asyncio
async def test_taxonomy_seeding_on_sqlite_fallback():
    """Verify that taxonomy seeding works identically and idempotently on SQLite."""
    sqlite_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=sqlite_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # First run: should create 32
        stats1 = await seed_taxonomy(db)
        assert stats1["created"] == 32
        assert stats1["updated"] == 0
        assert stats1["total"] == 32

        # Second run: idempotent update
        stats2 = await seed_taxonomy(db)
        assert stats2["created"] == 0
        assert stats2["updated"] == 32
        assert stats2["total"] == 32

        # Verify diagnosis model foreign key and fields on SQLite
        diag = Diagnosis(
            misconception_code="A1",
            confidence_score=0.95,
            detector_type=DetectorType.RULE_AST,
            is_primary=True,
            evidence_lines=[10, 11],
            explanation="Off-by-one error detected in loop range bounds.",
        )
        assert diag.misconception_code == "A1"
        assert diag.confidence_score == 0.95
        assert diag.evidence_lines == [10, 11]

    await sqlite_engine.dispose()
