# src/exceptions.py
"""
Custom exception classes for the application.

Provides structured error handling with specific exception types
for different error scenarios.
"""


class RAGAppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


# Database Exceptions
class DatabaseError(RAGAppError):
    """Base exception for database-related errors."""

    pass


class ConnectionError(DatabaseError):
    """Database connection failed."""

    pass


class QueryError(DatabaseError):
    """Database query execution failed."""

    pass


# Authentication Exceptions
class AuthenticationError(RAGAppError):
    """Base exception for authentication-related errors."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password."""

    def __init__(self):
        super().__init__("Invalid username or password")


class UserNotFoundError(AuthenticationError):
    """User not found."""

    def __init__(self, identifier: str):
        super().__init__(f"User not found: {identifier}")


class UserAlreadyExistsError(AuthenticationError):
    """User already exists."""

    def __init__(self, field: str, value: str):
        super().__init__(f"User with {field} '{value}' already exists")


# File Processing Exceptions
class FileProcessingError(RAGAppError):
    """Base exception for file processing errors."""

    pass


class FileUploadError(FileProcessingError):
    """File upload failed."""

    pass


class FileNotFoundError(FileProcessingError):
    """Requested file not found."""

    pass


class UnsupportedFileTypeError(FileProcessingError):
    """File type not supported."""

    def __init__(self, mime_type: str):
        super().__init__(f"Unsupported file type: {mime_type}")


# Gemini API Exceptions
class GeminiAPIError(RAGAppError):
    """Base exception for Gemini API errors."""

    pass


class GeminiUploadError(GeminiAPIError):
    """File upload to Gemini failed."""

    pass


class GeminiProcessingError(GeminiAPIError):
    """Gemini file processing failed."""

    pass


class GeminiChatError(GeminiAPIError):
    """Gemini chat session error."""

    pass


# Session Exceptions
class SessionError(RAGAppError):
    """Base exception for session-related errors."""

    pass


class SessionNotFoundError(SessionError):
    """Chat session not found."""

    def __init__(self, session_id: int):
        super().__init__(f"Chat session not found: {session_id}")


class SessionAccessDeniedError(SessionError):
    """User does not have access to this session."""

    def __init__(self, session_id: int):
        super().__init__(f"Access denied to session: {session_id}")

