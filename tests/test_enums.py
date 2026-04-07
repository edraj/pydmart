"""Tests for pydmart.enums."""

import pytest
from pydmart.enums import (
    Status,
    Language,
    UserType,
    QueryType,
    SortType,
    RequestType,
    ResourceAttachmentType,
    ResourceType,
    ContentType,
    ContentTypeMedia,
)


class TestStatus:
    def test_values(self):
        assert Status.success == "success"
        assert Status.failed == "failed"

    def test_membership(self):
        assert len(Status) == 2

    def test_is_str(self):
        assert isinstance(Status.success, str)


class TestLanguage:
    def test_values(self):
        assert Language.arabic == "arabic"
        assert Language.english == "english"
        assert Language.kurdish == "kurdish"
        assert Language.french == "french"
        assert Language.turkish == "turkish"

    def test_count(self):
        assert len(Language) == 5


class TestUserType:
    def test_values(self):
        assert UserType.web == "web"
        assert UserType.mobile == "mobile"
        assert UserType.bot == "bot"

    def test_count(self):
        assert len(UserType) == 3


class TestQueryType:
    EXPECTED = [
        "aggregation", "search", "subpath", "events", "history",
        "tags", "spaces", "counters", "reports", "attachments",
        "attachments_aggregation",
    ]

    def test_all_values_present(self):
        values = [e.value for e in QueryType]
        assert sorted(values) == sorted(self.EXPECTED)

    def test_count(self):
        assert len(QueryType) == 11

    def test_str_usage(self):
        assert f"type={QueryType.search}" == "type=search"


class TestSortType:
    def test_values(self):
        assert SortType.ascending == "ascending"
        assert SortType.descending == "descending"

    def test_count(self):
        assert len(SortType) == 2


class TestRequestType:
    EXPECTED = ["create", "update", "progress_ticket", "delete", "move", "update_acl", "assign"]

    def test_all_values_present(self):
        values = [e.value for e in RequestType]
        assert sorted(values) == sorted(self.EXPECTED)

    def test_count(self):
        assert len(RequestType) == 7


class TestResourceAttachmentType:
    EXPECTED = ["json", "comment", "media", "relationship", "alteration", "csv", "parquet", "jsonl", "sqlite"]

    def test_all_values_present(self):
        values = [e.value for e in ResourceAttachmentType]
        assert sorted(values) == sorted(self.EXPECTED)

    def test_count(self):
        assert len(ResourceAttachmentType) == 9


class TestResourceType:
    def test_count(self):
        assert len(ResourceType) == 26

    @pytest.mark.parametrize("name,value", [
        ("user", "user"),
        ("group", "group"),
        ("folder", "folder"),
        ("schema", "schema"),
        ("content", "content"),
        ("ticket", "ticket"),
        ("space", "space"),
        ("post", "post"),
        ("notification", "notification"),
    ])
    def test_selected_values(self, name: str, value: str):
        assert ResourceType[name] == value


class TestContentType:
    EXPECTED = [
        "text", "html", "markdown", "json", "image", "python",
        "pdf", "audio", "video", "jsonl", "csv", "sqlite", "parquet",
    ]

    def test_all_values_present(self):
        values = [e.value for e in ContentType]
        assert sorted(values) == sorted(self.EXPECTED)

    def test_count(self):
        assert len(ContentType) == 13


class TestContentTypeMedia:
    EXPECTED = ["text", "html", "markdown", "image", "python", "pdf", "audio", "video"]

    def test_all_values_present(self):
        values = [e.value for e in ContentTypeMedia]
        assert sorted(values) == sorted(self.EXPECTED)

    def test_count(self):
        assert len(ContentTypeMedia) == 8

    def test_subset_of_content_type(self):
        """All ContentTypeMedia values should also appear in ContentType."""
        ct_values = {e.value for e in ContentType}
        for media in ContentTypeMedia:
            assert media.value in ct_values
