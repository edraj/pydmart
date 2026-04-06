"""Tests for pydmart.consts regex constants."""

import re
import pytest
from pydmart.consts import SUBPATH, SHORTNAME, SPACENAME


class TestSubpath:
    """Validate the SUBPATH regex pattern."""

    @pytest.mark.parametrize("value", [
        "a",
        "hello",
        "hello/world",
        "path_with_underscores",
        "CamelCase",
        "abc123",
        "a" * 128,
        # Arabic characters
        "\u0627\u0628\u062a",
        # Mixed
        "docs/\u0627\u0628\u062a/page",
    ])
    def test_valid_subpaths(self, value: str):
        assert re.match(SUBPATH, value), f"Expected '{value}' to match SUBPATH"

    @pytest.mark.parametrize("value", [
        "",                # empty
        "a" * 129,         # too long
        "has spaces",
        "special!char",
        "dot.path",
        "dash-path",
    ])
    def test_invalid_subpaths(self, value: str):
        assert not re.match(SUBPATH, value), f"Expected '{value}' NOT to match SUBPATH"


class TestShortname:
    """Validate the SHORTNAME regex pattern."""

    @pytest.mark.parametrize("value", [
        "a",
        "hello",
        "user_name",
        "CamelCase",
        "abc123",
        "a" * 64,
        "\u0627\u0628\u062a",
    ])
    def test_valid_shortnames(self, value: str):
        assert re.match(SHORTNAME, value), f"Expected '{value}' to match SHORTNAME"

    @pytest.mark.parametrize("value", [
        "",
        "a" * 65,
        "has spaces",
        "has/slash",
        "has-dash",
        "dot.name",
    ])
    def test_invalid_shortnames(self, value: str):
        assert not re.match(SHORTNAME, value), f"Expected '{value}' NOT to match SHORTNAME"


class TestSpacename:
    """Validate the SPACENAME regex pattern."""

    @pytest.mark.parametrize("value", [
        "a",
        "myspace",
        "space_1",
        "a" * 32,
        "\u0627\u0628\u062a",
    ])
    def test_valid_spacenames(self, value: str):
        assert re.match(SPACENAME, value), f"Expected '{value}' to match SPACENAME"

    @pytest.mark.parametrize("value", [
        "",
        "a" * 33,
        "has spaces",
        "has/slash",
        "has-dash",
    ])
    def test_invalid_spacenames(self, value: str):
        assert not re.match(SPACENAME, value), f"Expected '{value}' NOT to match SPACENAME"
