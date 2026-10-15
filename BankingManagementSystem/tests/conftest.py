"""
Pytest configuration and fixtures.
Provides an isolated temporary database for test runs.
"""

import tempfile
from pathlib import Path
import pytest

from database import init_database


@pytest.fixture
def test_db_path():
    """
    Create a clean, isolated temporary SQLite database for each test,
    ensuring test isolation and zero interference with the project database.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)

    # Initialize tables and schema
    init_database(tmp_path)

    yield tmp_path

    # Clean up temporary database file
    try:
        if tmp_path.exists():
            tmp_path.unlink()
    except Exception:
        pass
