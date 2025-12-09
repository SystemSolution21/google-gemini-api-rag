# src/config.py
"""
Centralized configuration module.

Loads environment variables and provides configuration settings
for the application.
"""

# imports built-in modules
import logging
import os
import sys
from typing import Optional

# imports third-party modules
from dotenv import load_dotenv

# Use basic logger here to avoid circular import with src.utils.logger
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Google Gemini API
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")

    # Database
    DB_URL: Optional[str] = os.getenv("DB_URL")

    # Gemini Model Configuration
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "1"))
    GEMINI_TOP_P: float = float(os.getenv("GEMINI_TOP_P", "0.95"))
    GEMINI_TOP_K: int = int(os.getenv("GEMINI_TOP_K", "64"))
    GEMINI_MAX_OUTPUT_TOKENS: int = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "8192"))

    # File Upload
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    UPLOAD_TIMEOUT: int = int(os.getenv("UPLOAD_TIMEOUT", "180"))

    # Paths
    PUBLIC_DIR: str = os.getenv("PUBLIC_DIR", "public")
    LOGS_DIR: str = os.getenv("LOGS_DIR", "logs")

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration.

        Returns
        -------
        bool
            True if all required configuration is present.

        Raises
        ------
        SystemExit
            If required configuration is missing.
        """
        errors = []

        if not cls.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY environment variable not set")

        if not cls.DB_URL:
            errors.append("DB_URL environment variable not set")

        if errors:
            for error in errors:
                logger.error(f"❌ Configuration Error: {error}")
            return False

        return True

    @classmethod
    def validate_or_exit(cls) -> None:
        """Validate configuration and exit if invalid."""
        if not cls.validate():
            sys.exit(1)


# Create a singleton instance for easy access
config = Config()
