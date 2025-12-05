# src/db/models/document.py
"""
Document model with CRUD operations.
"""

from typing import Any, Dict, List, Optional

import asyncpg


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

