# src/db/models/user.py
"""
User model with authentication methods.
"""

from typing import Any, Dict, Optional

import asyncpg

from src.db.models.base import hash_password, verify_password


class User:
    """User model with authentication and CRUD operations."""

    @staticmethod
    async def create(
        conn: asyncpg.Connection, username: str, email: str, password: str
    ) -> Optional[int]:
        """Create a new user.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        username : str
            Unique username.
        email : str
            Unique email address.
        password : str
            Plain text password (will be hashed).

        Returns
        -------
        Optional[int]
            User ID if successful, None otherwise.
        """
        try:
            password_hash = hash_password(password)
            result = await conn.fetchrow(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                username,
                email,
                password_hash,
            )
            return result["id"] if result else None
        except asyncpg.UniqueViolationError:
            return None

    @staticmethod
    async def authenticate(
        conn: asyncpg.Connection, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        username : str
            Username or email.
        password : str
            Plain text password.

        Returns
        -------
        Optional[Dict[str, Any]]
            User data if authentication successful, None otherwise.
        """
        user = await conn.fetchrow(
            """
            SELECT id, username, email, password_hash
            FROM users
            WHERE username = $1 OR email = $1
            """,
            username,
        )

        if user and verify_password(password, user["password_hash"]):
            # Update last login
            await conn.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1",
                user["id"],
            )
            return {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
            }
        return None

    @staticmethod
    async def get_by_id(
        conn: asyncpg.Connection, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get user by ID.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        user_id : int
            User ID.

        Returns
        -------
        Optional[Dict[str, Any]]
            User data if found, None otherwise.
        """
        user = await conn.fetchrow(
            "SELECT id, username, email, created_at, last_login FROM users WHERE id = $1",
            user_id,
        )
        return dict(user) if user else None

    @staticmethod
    async def update_password(
        conn: asyncpg.Connection, username_or_email: str, new_password: str
    ) -> bool:
        """Update a user's password given their username or email.

        This helper is primarily used by development scripts and tests,
        but it may also be useful for future account management features.

        Parameters
        ----------
        conn : asyncpg.Connection
            Active database connection.
        username_or_email : str
            Username or email address identifying the user.
        new_password : str
            Plain text new password (will be hashed internally).

        Returns
        -------
        bool
            ``True`` if a row was updated (user existed), ``False`` otherwise.
        """
        # look up the user first
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE username = $1 OR email = $1",
            username_or_email,
        )
        if not user:
            return False

        password_hash = hash_password(new_password)
        result = await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2",
            password_hash,
            user["id"],
        )
        # asyncpg returns a string like 'UPDATE 1' when a row was affected
        return result.startswith("UPDATE") and result.endswith("1")
