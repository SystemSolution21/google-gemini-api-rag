# reset_data_only.py - Better for development
import asyncio
from database import get_pool

async def reset_data_only():
    """Reset data but keep schema - safe for development."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Truncate tables (faster than DELETE, resets sequences automatically)
        await conn.execute("TRUNCATE users, chat_sessions, messages, documents RESTART IDENTITY CASCADE")
        print("✅ All data reset, sequences restarted, schema preserved")

if __name__ == "__main__":
    asyncio.run(reset_data_only())