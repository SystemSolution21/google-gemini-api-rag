# auth.py
"""
Authentication module for Chainlit using custom password authentication.
Integrates with PostgreSQL database for user management.
"""

# imports built-in modules
from typing import Optional

# imports third-party modules
import chainlit as cl

# imports local modules
from database import get_pool
from models import User


@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """Authenticate user with username/email and password.

    This callback is called by Chainlit when a user attempts to log in.

    Parameters
    ----------
    username : str
        Username or email address.
    password : str
        Plain text password.

    Returns
    -------
    Optional[cl.User]
        Chainlit User object if authentication successful, None otherwise.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        user_data = await User.authenticate(conn, username, password)

        if user_data:
            return cl.User(
                identifier=user_data["username"],  # Use username instead of ID
                metadata={
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "user_id": user_data["id"],
                },
            )
        return None


async def register_user(username: str, email: str, password: str) -> Optional[int]:
    """Register a new user.

    Parameters
    ----------
    username : str
        Unique username.
    email : str
        Unique email address.
    password : str
        Plain text password (will be hashed).

    Returns
    -------
    Optional[int]
        User ID if registration successful, None if username/email already exists.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await User.create(conn, username, email, password)


def get_current_user_id() -> Optional[int]:
    """Get the current authenticated user's ID from the session.

    Returns
    -------
    Optional[int]
        User ID if authenticated, None otherwise.
    """
    user = cl.user_session.get("user")
    if user and user.metadata:
        return user.metadata.get("user_id")
    return None


def get_current_username() -> Optional[str]:
    """Get the current authenticated user's username from the session.

    Returns
    -------
    Optional[str]
        Username if authenticated, None otherwise.
    """
    user = cl.user_session.get("user")
    if user and user.metadata:
        return user.metadata.get("username")
    return None
