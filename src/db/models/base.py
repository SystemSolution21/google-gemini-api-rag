# src/db/models/base.py
"""
Base model utilities.

Contains common password hashing functionality and other shared utilities.
"""

# imports built-in modules
import hashlib
import secrets


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt.

    Parameters
    ----------
    password : str
        Plain text password.

    Returns
    -------
    str
        Hashed password with salt in format 'salt$hash'.
    """
    salt: str = secrets.token_hex(nbytes=16)
    pwd_hash: str = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


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
        salt, pwd_hash = password_hash.split(sep="$")
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except ValueError:
        return False
