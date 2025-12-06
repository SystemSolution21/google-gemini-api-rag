# scripts/dev/reset_data_only.py
"""
Reset all data but keep schema - safe for development.

WARNING: This will delete ALL data from the database!
Only use in development environments.

Usage:
    python scripts/dev/reset_data_only.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.db import get_pool
from src.utils.logger import get_db_logger

# Database logger
logger = get_db_logger()


async def reset_data_only():
    """Reset data but keep schema - safe for development."""
    logger.warning("⚠️ This will delete ALL data from the database!")
    confirm = input("Are you sure? (type 'yes' to confirm): ").strip().lower()

    if confirm != "yes":
        logger.info("❌ Operation aborted by user.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Truncate tables (faster than DELETE, resets sequences automatically)
        await conn.execute(
            "TRUNCATE users, chat_sessions, messages, documents RESTART IDENTITY CASCADE"
        )
        logger.info("✅ All data reset, sequences restarted, schema preserved")


if __name__ == "__main__":
    asyncio.run(reset_data_only())
