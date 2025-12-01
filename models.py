# models.py
"""
Database models and CRUD operations for users, chat sessions, messages, and documents.
"""

# imports built-in modules
import hashlib
import secrets
from typing import Any, Dict, List, Optional

# imports third-party modules
import asyncpg


class User:
    """User model with authentication methods."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256 with salt.

        Parameters
        ----------
        password : str
            Plain text password.

        Returns
        -------
        str
            Hashed password with salt.
        """
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${pwd_hash}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Parameters
        ----------
        password : str
            Plain text password to verify.
        password_hash : str
            Stored password hash with salt.

        Returns
        -------
        bool
            True if password matches, False otherwise.
        """
        try:
            salt, pwd_hash = password_hash.split("$")
            return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
        except ValueError:
            return False

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
            password_hash = User.hash_password(password)
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

        if user and User.verify_password(password, user["password_hash"]):
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


class Document:
    """Document model with CRUD operations."""

    @staticmethod
    async def create(
        conn: asyncpg.Connection,
        chat_session_id: int,
        filename: str,
        file_path: str,
        gemini_file_uri: Optional[str] = None,
        gemini_file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        file_size: Optional[int] = None,
    ) -> Optional[int]:
        """Create a new document record.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        chat_session_id : int
            Chat session ID.
        filename : str
            Original filename.
        file_path : str
            Path where file is stored.
        gemini_file_uri : Optional[str]
            Gemini API file URI.
        gemini_file_name : Optional[str]
            Gemini API file name.
        mime_type : Optional[str]
            File MIME type.
        file_size : Optional[int]
            File size in bytes.

        Returns
        -------
        Optional[int]
            Document ID if successful, None otherwise.
        """
        result = await conn.fetchrow(
            """
            INSERT INTO documents (
                chat_session_id, filename, file_path, gemini_file_uri,
                gemini_file_name, mime_type, file_size
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            chat_session_id,
            filename,
            file_path,
            gemini_file_uri,
            gemini_file_name,
            mime_type,
            file_size,
        )
        return result["id"] if result else None

    @staticmethod
    async def list_by_session(
        conn: asyncpg.Connection, chat_session_id: int
    ) -> List[Dict[str, Any]]:
        """List all documents in a chat session.

        Parameters
        ----------
        conn : asyncpg.Connection
            Database connection.
        chat_session_id : int
            Chat session ID.

        Returns
        -------
        List[Dict[str, Any]]
            List of documents.
        """
        documents = await conn.fetch(
            """
            SELECT id, filename, file_path, gemini_file_uri, gemini_file_name,
                   mime_type, file_size, uploaded_at
            FROM documents
            WHERE chat_session_id = $1
            ORDER BY uploaded_at DESC
            """,
            chat_session_id,
        )
        return [dict(d) for d in documents]
