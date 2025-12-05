# tests/conftest.py
"""
Pytest configuration and fixtures.

This module provides shared fixtures and configuration for all tests.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests.

    This fixture creates a single event loop for the entire test session.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_env() -> dict:
    """Provide test environment variables.

    Returns a dictionary of environment variables for testing.
    Override these in your test environment.
    """
    return {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", "test_api_key"),
        "DB_URL": os.getenv("TEST_DB_URL", "postgresql://test:test@localhost/test_db"),
    }


@pytest.fixture
def temp_public_dir(tmp_path: Path) -> Path:
    """Create a temporary public directory for file tests.

    Parameters
    ----------
    tmp_path : Path
        Pytest's temporary path fixture.

    Returns
    -------
    Path
        Path to the temporary public directory.
    """
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    return public_dir


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Provide sample PDF content for testing.

    Returns
    -------
    bytes
        Minimal valid PDF content.
    """
    # Minimal valid PDF
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""

