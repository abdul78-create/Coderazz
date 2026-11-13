"""CLI script to idempotently seed the 30-class + 2 meta-class misconception taxonomy."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.database import get_session_factory
from backend.app.services.taxonomy_seed import TAXONOMY_DEFINITIONS, seed_taxonomy


async def main() -> None:
    print(f"[*] Starting taxonomy seeding ({len(TAXONOMY_DEFINITIONS)} definitions)...")
    factory = get_session_factory()
    async with factory() as db:
        stats = await seed_taxonomy(db)
        print(f"[+] Seeding complete: {stats['created']} created, {stats['updated']} updated, {stats['total']} total.")


if __name__ == "__main__":
    asyncio.run(main())
