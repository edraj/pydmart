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


# aioresponses 0.7.9, the latest, builds its responses without the
# `stream_writer` argument aiohttp 3.14 added to ClientResponse, so every mocked
# request failed. Supply a finished writer until aioresponses does; once it
# passes its own, setdefault leaves that alone.
import aioresponses.core  # noqa: E402
from unittest.mock import Mock  # noqa: E402
from aiohttp import ClientResponse  # noqa: E402


class _Response(ClientResponse):
    def __init__(self, method, url, **kwargs):
        kwargs.setdefault("stream_writer", Mock(output_size=0))
        super().__init__(method, url, **kwargs)


aioresponses.core.ClientResponse = _Response
