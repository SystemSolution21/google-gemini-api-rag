# src/db/models/message.py
"""
Message model with CRUD operations.
"""

from typing import Any, Dict, List, Optional

import asyncpg


class Message:
    """Message model with CRUD operations."""

    @staticmethod
    async def create(
        conn: asyncpg.Connection, chat_session_id: int, role: str, content: str
    ) -> Optional[int]:
        """Create a new message.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        chat_session_id : int
            Chat session ID.
        role : str
            Message role ('user' or 'assistant').
        content : str
            Message content.

        Returns
        -------
        Optional[int]
            Message ID if successful, None otherwise.
        """
        result = await conn.fetchrow(
            """
            INSERT INTO messages (chat_session_id, role, content)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            chat_session_id,
            role,
            content,
        )

        # Update chat session's updated_at timestamp
        await conn.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = $1",
            chat_session_id,
        )

        return result["id"] if result else None

    @staticmethod
    async def list_by_session(
        conn: asyncpg.Connection, chat_session_id: int
    ) -> List[Dict[str, Any]]:
        """List all messages in a chat session.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        chat_session_id : int
            Chat session ID.

        Returns
        -------
        List[Dict[str, Any]]
            List of messages ordered by creation time.
        """
        messages = await conn.fetch(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE chat_session_id = $1
            ORDER BY created_at ASC
            """,
            chat_session_id,
        )
        return [dict(m) for m in messages]

