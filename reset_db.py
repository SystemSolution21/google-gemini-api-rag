# reset_db.py
"""
Script to delete all database records for testing and debugging purposes.
Use with caution in production!
"""

# imports built-in modules
import asyncio

# imports local modules
from database import get_pool


async def reset_database():
    """Delete all records and reset sequences."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Delete records
        await conn.execute("DELETE FROM messages")
        await conn.execute("DELETE FROM documents")
        await conn.execute("DELETE FROM chat_sessions")
        await conn.execute("DELETE FROM users")

        # Reset auto-increment sequences
        await conn.execute("ALTER SEQUENCE users_id_seq RESTART WITH 1")
        await conn.execute("ALTER SEQUENCE chat_sessions_id_seq RESTART WITH 1")
        await conn.execute("ALTER SEQUENCE messages_id_seq RESTART WITH 1")
        await conn.execute("ALTER SEQUENCE documents_id_seq RESTART WITH 1")

        print("✅ All database records deleted and sequences reset")


if __name__ == "__main__":
    asyncio.run(reset_database())
