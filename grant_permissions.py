# grant_permissions.py
"""
Grant necessary schema permissions for PostgreSQL 15+.
Run this script as postgres superuser before running setup_db.py.

Usage:
    python grant_permissions.py

This script will prompt for postgres password and grant all necessary
permissions to gemini_user on the public schema.
"""

# imports built-in modules
import os
import subprocess
import sys

# imports third-party modules
from dotenv import load_dotenv

load_dotenv()

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
    if not database_url:
        return "gemini_rag"
    # Format: postgresql://user:pass@host:port/dbname
    try:
        return database_url.split("/")[-1].split("?")[0]
    except (IndexError, AttributeError):
        return "gemini_rag"


def get_username_from_url() -> str:
    """Extract username from DB_URL."""
    database_url = os.getenv("DB_URL", "")
    if not database_url:
        return "gemini_user"
    # Format: postgresql://user:pass@host:port/dbname
    try:
        return database_url.split("://")[1].split(":")[0]
    except (IndexError, AttributeError):
        return "gemini_user"


def main():
    """Main function to grant permissions."""
    print("🔐 PostgreSQL Schema Permission Grant Tool")
    print("=" * 50)
    print()
    print("This script grants necessary permissions for PostgreSQL 15+")
    print("Run this BEFORE running setup_db.py")
    print()

    db_name = get_db_name_from_url()
    db_user = get_username_from_url()

    print(f"Database: {db_name}")
    print(f"User to grant permissions: {db_user}")
    print()

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

    print("Running grant commands...")
    print()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            print("✅ Permissions granted successfully!")
            print()
            print("Output:")
            print(result.stdout)
            print()
            print("You can now run: python setup_db.py")
        else:
            print("❌ Error granting permissions:")
            print(result.stderr)
            print()
            print("You may need to run the following command manually:")
            print()
            print(
                f'psql -U postgres -d {db_name} -c "{sql.strip().replace(chr(10), " ")}"'
            )
            sys.exit(1)

    except FileNotFoundError:
        print("❌ psql command not found.")
        print("Make sure PostgreSQL is installed and psql is in your PATH.")
        print()
        print("Run the following command manually in psql:")
        print()
        print("# Connect to database:")
        print(f"psql -U postgres -d {db_name}")
        print()
        print("# Then run:")
        print(sql)
        sys.exit(1)


if __name__ == "__main__":
    main()
