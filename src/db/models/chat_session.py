# src/db/models/chat_session.py
"""
Chat session model with CRUD operations.
"""

from typing import Any, Dict, List, Optional

import asyncpg


class ChatSession:
    """Chat session model with CRUD operations."""

    @staticmethod
    async def create(
        conn: asyncpg.Connection, user_id: int, title: str
    ) -> Optional[int]:
        """Create a new chat session.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        user_id : int
            User ID who owns this session.
        title : str
            Session title.

        Returns
        -------
        Optional[int]
            Chat session ID if successful, None otherwise.
        """
        result = await conn.fetchrow(
            """
            INSERT INTO chat_sessions (user_id, title)
            VALUES ($1, $2)
            RETURNING id
            """,
            user_id,
            title,
        )
        return result["id"] if result else None

    @staticmethod
    async def get_by_id(
        conn: asyncpg.Connection, session_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get chat session by ID (with user ownership check).

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        session_id : int
            Chat session ID.
        user_id : int
            User ID for ownership verification.

        Returns
        -------
        Optional[Dict[str, Any]]
            Session data if found and owned by user, None otherwise.
        """
        session = await conn.fetchrow(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM chat_sessions
            WHERE id = $1 AND user_id = $2 AND is_deleted = FALSE
            """,
            session_id,
            user_id,
        )
        return dict(session) if session else None

    @staticmethod
    async def list_by_user(
        conn: asyncpg.Connection, user_id: int
    ) -> List[Dict[str, Any]]:
        """List all chat sessions for a user.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        user_id : int
            User ID.

        Returns
        -------
        List[Dict[str, Any]]
            List of chat sessions.
        """
        sessions = await conn.fetch(
            """
            SELECT id, title, created_at, updated_at
            FROM chat_sessions
            WHERE user_id = $1 AND is_deleted = FALSE
            ORDER BY updated_at DESC
            """,
            user_id,
        )
        return [dict(s) for s in sessions]

    @staticmethod
    async def count_by_user(conn: asyncpg.Connection, user_id: int) -> int:
        """Count total chat sessions for a user (including deleted).

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        user_id : int
            User ID.

        Returns
        -------
        int
            Total count of chat sessions.
        """
        result = await conn.fetchval(
            """
            SELECT COUNT(*) FROM chat_sessions WHERE user_id = $1
            """,
            user_id,
        )
        return result or 0

    @staticmethod
    async def update_title(
        conn: asyncpg.Connection, session_id: int, user_id: int, new_title: str
    ) -> bool:
        """Update chat session title.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        session_id : int
            Chat session ID.
        user_id : int
            User ID for ownership verification.
        new_title : str
            New title.

        Returns
        -------
        bool
            True if updated successfully, False otherwise.
        """
        result = await conn.execute(
            """
            UPDATE chat_sessions
            SET title = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2 AND user_id = $3 AND is_deleted = FALSE
            """,
            new_title,
            session_id,
            user_id,
        )
        return result != "UPDATE 0"

    @staticmethod
    async def delete(conn: asyncpg.Connection, session_id: int, user_id: int) -> bool:
        """Soft delete a chat session.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        session_id : int
            Chat session ID.
        user_id : int
            User ID for ownership verification.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        result = await conn.execute(
            """
            UPDATE chat_sessions
            SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND user_id = $2
            """,
            session_id,
            user_id,
        )
        return result != "UPDATE 0"

    @staticmethod
    async def hard_delete(
        conn: asyncpg.Connection, session_id: int, user_id: int
    ) -> bool:
        """Hard delete a chat session and all related records.

        Deletes messages and documents first, then the chat session.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        session_id : int
            Chat session ID.
        user_id : int
            User ID for ownership verification.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        # Verify ownership first
        session = await conn.fetchrow(
            "SELECT id FROM chat_sessions WHERE id = $1 AND user_id = $2",
            session_id,
            user_id,
        )
        if not session:
            return False

        # Delete documents first
        await conn.execute(
            "DELETE FROM documents WHERE chat_session_id = $1",
            session_id,
        )

        # Delete messages
        await conn.execute(
            "DELETE FROM messages WHERE chat_session_id = $1",
            session_id,
        )

        # Delete chat session
        result = await conn.execute(
            "DELETE FROM chat_sessions WHERE id = $1 AND user_id = $2",
            session_id,
            user_id,
        )
        return result != "DELETE 0"
