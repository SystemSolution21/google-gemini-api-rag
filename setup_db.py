# setup_db.py
"""
Database setup script to initialize schema and create admin user.
Run this script once before starting the application.
"""

# imports built-in modules
import asyncio
import sys

# imports local modules
from database import close_pool, get_pool, init_database
from models import User


async def create_admin_user():
    """Create an admin user interactively."""
    print("\n=== Create Admin User ===")
    username = input("Enter admin username: ").strip()
    email = input("Enter admin email: ").strip()
    password = input("Enter admin password: ").strip()
    password_confirm = input("Confirm password: ").strip()

    if password != password_confirm:
        print("❌ Passwords do not match!")
        return False

    if not username or not email or not password:
        print("❌ All fields are required!")
        return False

    pool = await get_pool()
    async with pool.acquire() as conn:
        user_id = await User.create(conn, username, email, password)

        if user_id:
            print(f"✅ Admin user created successfully! User ID: {user_id}")
            return True
        else:
            print("❌ Failed to create user. Username or email might already exist.")
            return False


async def main():
    """Main setup function."""
    print("🚀 Starting database setup...")

    try:
        # Initialize database schema
        await init_database()

        # Ask if user wants to create admin account
        create_admin = (
            input("\nDo you want to create an admin user? (y/n): ").strip().lower()
        )

        if create_admin == "y":
            await create_admin_user()

        print("\n✅ Database setup complete!")
        print("\nYou can now run the application with:")
        print("  chainlit run app.py -w")

    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
