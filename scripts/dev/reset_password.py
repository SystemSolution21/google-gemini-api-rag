# scripts/dev/reset_password.py
"""
Reset a single user's password - development helper.

This script should only be run in a non-production database since it bypasses
standard authentication and password recovery flows. It looks up a user by
username or email address and overwrites the stored password hash with a
new value typed by the operator.

Usage:
    python scripts/dev/reset_password.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.db.models import User
from src.db.connection import get_pool
from src.config import config
from src.utils.logger import get_db_logger

# Database logger
logger = get_db_logger()


async def reset_password():
    """Prompt for username/email and new password, then update DB."""

    # ensure configuration is valid before attempting a connection
    config.validate_or_exit()

    logger.warning("⚠️ This will reset a user's password in the database!")
    identifier = input("Enter username or email: ").strip()
    if not identifier:
        logger.info("❌ Operation aborted by user.")
        return

    new_password = input("Enter a new password: ").strip()
    if not new_password:
        logger.info("❌ Operation aborted by user.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        updated = await User.update_password(conn, identifier, new_password)
        if not updated:
            logger.error(f"❌ User '{identifier}' not found in database.")
            return

        logger.info(f"✅ Password reset for user '{identifier}'.")


if __name__ == "__main__":
    asyncio.run(reset_password())
