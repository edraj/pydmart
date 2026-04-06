"""Shared fixtures for pydmart tests."""

import sys
import os
import pytest

# Ensure the src package and tests helpers are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from helpers import BASE_URL  # noqa: E402


@pytest.fixture
def base_url() -> str:
    return BASE_URL


@pytest.fixture
def service():
    """Create a DmartService instance (not connected)."""
    from pydmart.service import DmartService
    return DmartService(BASE_URL)
