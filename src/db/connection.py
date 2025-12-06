# src/db/connection.py
"""
Database connection management module.

Handles PostgreSQL connection pool creation, schema initialization,
and connection lifecycle management.
"""

# imports built-in modules
from typing import Optional

# imports third-party modules
import asyncpg

# imports local modules
from src.config import config
from src.utils.logger import get_db_logger

# Database logger
logger = get_db_logger()

# Database connection pool
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool.

    Returns
    -------
    asyncpg.Pool
        The database connection pool.

    Raises
    ------
    ValueError
        If DB_URL environment variable is not set.
    """
    global _pool
    if _pool is None:
        if not config.DB_URL:
            raise ValueError("DB_URL environment variable not set")

        _pool = await asyncpg.create_pool(config.DB_URL)
    return _pool


async def close_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_database() -> None:
    """Initialize database schema with all required tables."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Create users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)

        # Create chat_sessions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT FALSE
            )
        """)

        # Create messages table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                chat_session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create documents table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                chat_session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                filename VARCHAR(500) NOT NULL,
                file_path VARCHAR(1000) NOT NULL,
                gemini_file_uri VARCHAR(1000),
                gemini_file_name VARCHAR(500),
                mime_type VARCHAR(100),
                file_size INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for better performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id 
            ON chat_sessions(user_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_chat_session_id 
            ON messages(chat_session_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_chat_session_id
            ON documents(chat_session_id)
        """)

        logger.info("[OK] Database schema initialized successfully")
