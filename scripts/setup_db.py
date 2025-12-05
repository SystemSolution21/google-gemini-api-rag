# scripts/setup_db.py
"""
Database setup script to initialize schema and create admin user.
Run this script once before starting the application.

Usage:
    python scripts/setup_db.py
"""

# imports built-in modules
import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# imports local modules
from src.db import User, close_pool, get_pool, init_database
from src.utils.logger import get_db_logger

logger = get_db_logger()


async def create_admin_user():
    """Create an admin user interactively."""
    logger.info("=== Create Admin User ===")
    username = input("Enter admin username: ").strip()
    email = input("Enter admin email: ").strip()
    password = input("Enter admin password: ").strip()
    password_confirm = input("Confirm password: ").strip()

    if password != password_confirm:
        logger.error("[ERROR] Passwords do not match!")
        return False

    if not username or not email or not password:
        logger.error("[ERROR] All fields are required!")
        return False

    pool = await get_pool()
    async with pool.acquire() as conn:
        user_id = await User.create(conn, username, email, password)

        if user_id:
            logger.info(f"[OK] Admin user created successfully! User ID: {user_id}")
            return True
        else:
            logger.error(
                "[ERROR] Failed to create user. Username or email might already exist."
            )
            return False


async def main():
    """Main setup function."""
    logger.info("[SETUP] Starting database setup...")

    try:
        # Initialize database schema
        await init_database()

        # Ask if user wants to create admin account
        create_admin = (
            input("\nDo you want to create an admin user? (y/n): ").strip().lower()
        )

        if create_admin == "y":
            await create_admin_user()

        logger.info("[OK] Database setup complete!")
        logger.info(
            "You can now run the application with: chainlit run app_multiuser.py -w"
        )

    except Exception as e:
        logger.error(f"[ERROR] Error during setup: {e}")
        sys.exit(1)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
