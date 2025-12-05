# src/db/__init__.py
"""
Database package.

Contains database connection management and data models.
"""

from src.db.connection import close_pool, get_pool, init_database
from src.db.models import ChatSession, Document, Message, User

__all__ = [
    "get_pool",
    "close_pool",
    "init_database",
    "User",
    "ChatSession",
    "Message",
    "Document",
]

