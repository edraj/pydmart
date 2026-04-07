"""Tests for pydmart package-level exports."""

import pydmart


class TestPublicExports:
    """Every symbol in __all__ must be importable from the top-level package."""

    def test_all_defined(self):
        assert hasattr(pydmart, "__all__")
        assert len(pydmart.__all__) > 0

    def test_all_symbols_importable(self):
        for name in pydmart.__all__:
            obj = getattr(pydmart, name, None)
            assert obj is not None, f"pydmart.{name} is not importable"

    # -- Service --
    def test_dmart_service(self):
        assert pydmart.DmartService is not None

    # -- Models --
    def test_api_response(self):
        assert pydmart.ApiResponse is not None

    def test_api_response_record(self):
        assert pydmart.ApiResponseRecord is not None

    def test_action_response(self):
        assert pydmart.ActionResponse is not None

    def test_action_request(self):
        assert pydmart.ActionRequest is not None

    def test_action_request_record(self):
        assert pydmart.ActionRequestRecord is not None

    def test_query_request(self):
        assert pydmart.QueryRequest is not None

    def test_response_entry(self):
        assert pydmart.ResponseEntry is not None

    def test_response_record(self):
        assert pydmart.ResponseRecord is not None

    def test_error(self):
        assert pydmart.Error is not None

    def test_dmart_exception(self):
        assert pydmart.DmartException is not None

    def test_payload(self):
        assert pydmart.Payload is not None

    def test_translation(self):
        assert pydmart.Translation is not None

    def test_permission(self):
        assert pydmart.Permission is not None

    def test_meta_extended(self):
        assert pydmart.MetaExtended is not None

    def test_aggregation_type(self):
        assert pydmart.AggregationType is not None

    def test_aggregation_reducer(self):
        assert pydmart.AggregationReducer is not None

    # -- Enums --
    def test_status(self):
        assert pydmart.Status.success == "success"

    def test_language(self):
        assert pydmart.Language.english == "english"

    def test_user_type(self):
        assert pydmart.UserType.web == "web"

    def test_query_type(self):
        assert pydmart.QueryType.search == "search"

    def test_sort_type(self):
        assert pydmart.SortType.ascending == "ascending"

    def test_request_type(self):
        assert pydmart.RequestType.create == "create"

    def test_resource_attachment_type(self):
        assert pydmart.ResourceAttachmentType.json == "json"

    def test_resource_type(self):
        assert pydmart.ResourceType.content == "content"

    def test_content_type(self):
        assert pydmart.ContentType.json == "json"

    def test_content_type_media(self):
        assert pydmart.ContentTypeMedia.image == "image"

    # -- Constants --
    def test_subpath(self):
        assert isinstance(pydmart.SUBPATH, str)
        assert pydmart.SUBPATH.startswith("^")

    def test_shortname(self):
        assert isinstance(pydmart.SHORTNAME, str)

    def test_spacename(self):
        assert isinstance(pydmart.SPACENAME, str)
