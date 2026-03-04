from unittest.mock import AsyncMock

import pytest

from src.db.models.user import User


@pytest.mark.asyncio
async def test_update_password_existing_user():
    """Test password update for an existing user (by username)."""
    # Mock connection
    mock_conn = AsyncMock()

    # Simulate: user exists in database
    mock_conn.fetchrow = AsyncMock(return_value={"id": 42})

    # Simulate: UPDATE succeeds
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    # Call the method
    result = await User.update_password(mock_conn, "alice", "newpass")

    # Verify it returned True
    assert result is True

    # Verify it looked up the user first
    mock_conn.fetchrow.assert_called_once()
    call_args = mock_conn.fetchrow.call_args
    assert "alice" in call_args[0]  # username was in the query

    # Verify it executed the UPDATE
    mock_conn.execute.assert_called_once()
    execute_call = mock_conn.execute.call_args
    assert "UPDATE" in execute_call[0][0].upper()
    assert 42 in execute_call[0]  # user ID was passed


@pytest.mark.asyncio
async def test_update_password_by_email():
    """Test password update for an existing user (by email)."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"id": 99})
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    result = await User.update_password(mock_conn, "alice@example.com", "newpass")

    assert result is True
    mock_conn.fetchrow.assert_called_once()
    # Verify email was in the query
    call_args = mock_conn.fetchrow.call_args
    assert "alice@example.com" in call_args[0]


@pytest.mark.asyncio
async def test_update_password_nonexistent_user():
    """Test password update returns False when user not found."""
    mock_conn = AsyncMock()

    # Simulate: user not found
    mock_conn.fetchrow = AsyncMock(return_value=None)

    result = await User.update_password(mock_conn, "noone", "anypass")

    # Should return False
    assert result is False

    # Should only call fetchrow (lookup), not execute (update)
    mock_conn.fetchrow.assert_called_once()
    mock_conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_update_password_hashes_password():
    """Test that password is hashed before storing."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"id": 1})
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")

    await User.update_password(mock_conn, "user", "mypassword")

    # Get the password_hash that was passed to execute
    execute_call = mock_conn.execute.call_args
    password_hash = execute_call[0][1]  # Second argument to execute

    # Password should be hashed (contains $ separator)
    assert "$" in password_hash
    # Should NOT be the plaintext password
    assert password_hash != "mypassword"
