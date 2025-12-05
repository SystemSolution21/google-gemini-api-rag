# scripts/grant_permissions.py
"""
Grant necessary schema permissions for PostgreSQL 15+.
Run this script as postgres superuser before running setup_db.py.

Usage:
    python scripts/grant_permissions.py

This script will prompt for postgres password and grant all necessary
permissions to gemini_user on the public schema.
"""

# imports built-in modules
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# imports third-party modules
from dotenv import load_dotenv

from src.utils.logger import get_db_logger

load_dotenv()

logger = get_db_logger()

# SQL commands to grant permissions
GRANT_SQL = """
GRANT ALL ON SCHEMA public TO gemini_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gemini_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gemini_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO gemini_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO gemini_user;
"""


def get_db_name_from_url() -> str:
    """Extract database name from DB_URL."""
    database_url = os.getenv("DB_URL", "")
    try:
        parsed_url = urlparse(database_url)
        # The path will be '/dbname', so we strip the leading '/'
        db_name = parsed_url.path.lstrip("/")
        return db_name or "gemini_rag"
    except Exception:
        return "gemini_rag"


def get_username_from_url() -> str:
    """Extract username from DB_URL."""
    database_url = os.getenv("DB_URL", "")
    try:
        parsed_url = urlparse(database_url)
        return parsed_url.username or "gemini_user"
    except Exception:
        return "gemini_user"


def main():
    """Main function to grant permissions."""
    logger.info("[GRANT] PostgreSQL Schema Permission Grant Tool")
    logger.info("=" * 50)
    logger.info("This script grants necessary permissions for PostgreSQL 15+")
    logger.info("Run this BEFORE running setup_db.py")

    db_name = get_db_name_from_url()
    db_user = get_username_from_url()

    logger.info(f"Database: {db_name}")
    logger.info(f"User to grant permissions: {db_user}")

    # Build the SQL with actual username
    sql = GRANT_SQL.replace("gemini_user", db_user)

    # Build psql command
    cmd = [
        "psql",
        "-U",
        "postgres",
        "-d",
        db_name,
        "-c",
        sql.strip().replace("\n", " "),
    ]

    logger.info("Running grant commands...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            logger.info("[OK] Permissions granted successfully!")
            logger.info(f"Output: {result.stdout}")
            logger.info("You can now run: python scripts/setup_db.py")
        else:
            logger.error("[ERROR] Error granting permissions:")
            logger.error(result.stderr)
            logger.info("You may need to run the following command manually:")
            logger.info(
                f'psql -U postgres -d {db_name} -c "{sql.strip().replace(chr(10), " ")}"'
            )
            sys.exit(1)

    except FileNotFoundError:
        logger.error("[ERROR] psql command not found.")
        logger.info("Make sure PostgreSQL is installed and psql is in your PATH.")
        logger.info("Run the following command manually in psql:")
        logger.info(f"# Connect to database: psql -U postgres -d {db_name}")
        logger.info(f"# Then run: {sql}")
        sys.exit(1)


if __name__ == "__main__":
    main()
