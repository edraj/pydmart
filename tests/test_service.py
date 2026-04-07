"""Tests for pydmart.service.DmartService.

All HTTP calls are intercepted by aioresponses so no real network
traffic is generated.
"""

import io
import pytest
import aiohttp
from aioresponses import aioresponses

from pydmart.service import DmartService
from pydmart.models import (
    ApiResponse,
    DmartException,
    QueryRequest,
    ActionRequest,
    ActionRequestRecord,
    ResponseEntry,
)
from pydmart.enums import QueryType, ResourceType, RequestType, ContentType

from helpers import (
    BASE_URL,
    make_success_response,
    make_failed_response,
    make_login_response,
    make_profile_response,
    make_entry_response,
)


# ---------------------------------------------------------------------------
# Construction / lifecycle
# ---------------------------------------------------------------------------
class TestServiceInit:
    def test_defaults(self):
        svc = DmartService("http://localhost:8282")
        assert svc.base_url == "http://localhost:8282"
        assert svc.auth_token == ""
        assert svc.current_user_roles == []
        assert svc.current_user_permissions == []
        assert svc._session is None

    def test_instance_isolation(self):
        """Mutable defaults must not be shared across instances."""
        a = DmartService("http://a")
        b = DmartService("http://b")
        a.current_user_roles.append("admin")
        assert b.current_user_roles == []

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with DmartService(BASE_URL) as svc:
            assert svc._session is not None
            assert not svc._session.closed
        # after exit session should be closed
        assert svc._session is None

    @pytest.mark.asyncio
    async def test_connect_close(self):
        svc = DmartService(BASE_URL)
        await svc.connect()
        assert svc._session is not None
        sess = svc._session
        await svc.connect()  # idempotent
        assert svc._session is sess
        await svc.close()
        assert svc._session is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        svc = DmartService(BASE_URL)
        await svc.close()  # should not raise


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------
class TestHeaders:
    def test_json_headers_no_token(self):
        svc = DmartService(BASE_URL)
        h = svc.json_headers
        assert h["Content-Type"] == "application/json"
        assert h["Authorization"] == ""

    def test_json_headers_with_token(self):
        svc = DmartService(BASE_URL)
        svc.auth_token = "tok123"
        assert svc.json_headers["Authorization"] == "Bearer tok123"

    def test_headers_no_token(self):
        svc = DmartService(BASE_URL)
        assert svc.headers["Authorization"] == ""

    def test_headers_with_token(self):
        svc = DmartService(BASE_URL)
        svc.auth_token = "tok123"
        assert svc.headers["Authorization"] == "Bearer tok123"


# ---------------------------------------------------------------------------
# _request (low-level)
# ---------------------------------------------------------------------------
class TestRequest:
    @pytest.mark.asyncio
    async def test_success(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/test", payload=make_success_response())
                resp = await svc._request("GET", f"{BASE_URL}/test")
                assert isinstance(resp, ApiResponse)
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_failed_status_raises(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/test", payload=make_failed_response())
                with pytest.raises(DmartException) as exc_info:
                    await svc._request("GET", f"{BASE_URL}/test")
                assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_malformed_json_raises(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                # Missing 'status' key triggers the inner except
                m.get(f"{BASE_URL}/test", payload={"unexpected": True})
                with pytest.raises(DmartException) as exc_info:
                    await svc._request("GET", f"{BASE_URL}/test")
                assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_client_error_raises(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/test", exception=aiohttp.ClientError("conn refused"))
                with pytest.raises(DmartException) as exc_info:
                    await svc._request("GET", f"{BASE_URL}/test")
                assert exc_info.value.status_code == 500
                assert "conn refused" in exc_info.value.error.message


# ---------------------------------------------------------------------------
# Login / Auth
# ---------------------------------------------------------------------------
class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success_stores_token(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/login", payload=make_login_response("my_token"))
                resp = await svc.login("admin", "pass")
                assert svc.auth_token == "my_token"
                assert isinstance(resp, ApiResponse)

    @pytest.mark.asyncio
    async def test_login_no_records_raises(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/login", payload=make_success_response(records=[]))
                with pytest.raises(DmartException) as exc_info:
                    await svc.login("admin", "pass")
                assert "no records" in exc_info.value.error.message

    @pytest.mark.asyncio
    async def test_login_failed_raises(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/login", payload=make_failed_response(message="bad creds"))
                with pytest.raises(DmartException):
                    await svc.login("admin", "wrong")

    @pytest.mark.asyncio
    async def test_login_empty_attributes_no_crash(self):
        """Login record with no access_token should not crash."""
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                payload = make_success_response(records=[{
                    "resource_type": "user",
                    "shortname": "u",
                    "subpath": "/",
                    "attributes": {},
                }])
                m.post(f"{BASE_URL}/user/login", payload=payload)
                await svc.login("u", "p")
                assert svc.auth_token == ""


class TestLoginBy:
    @pytest.mark.asyncio
    async def test_login_by_stores_token(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/login", payload=make_login_response("by_tok"))
                resp = await svc.login_by({"email": "a@b.com"}, "pass")
                assert svc.auth_token == "by_tok"
                assert isinstance(resp, ApiResponse)

    @pytest.mark.asyncio
    async def test_login_by_no_records(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/login", payload=make_success_response())
                resp = await svc.login_by({"email": "a@b.com"}, "pass")
                assert svc.auth_token == ""  # unchanged


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout(self):
        async with DmartService(BASE_URL) as svc:
            svc.auth_token = "tok"
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/logout", payload=make_success_response())
                resp = await svc.logout()
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------
class TestUserManagement:
    @pytest.mark.asyncio
    async def test_create_user(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/create", payload=make_success_response())
                resp = await svc.create_user({"shortname": "new"})
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_update_user(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/profile", payload=make_success_response())
                resp = await svc.update_user({"displayname": "New Name"})
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_check_existing(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/user/check-existing?email=a@b.com", payload=make_success_response())
                resp = await svc.check_existing("email", "a@b.com")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_user_reset(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/reset", payload=make_success_response())
                resp = await svc.user_reset("baduser")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_validate_password(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/validate_password", payload=make_success_response())
                resp = await svc.validate_password("Str0ng!Pass")
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class TestGetProfile:
    @pytest.mark.asyncio
    async def test_caches_roles_and_permissions(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/user/profile", payload=make_profile_response(
                    roles=["editor"], permissions=["read"],
                ))
                resp = await svc.get_profile()
                assert svc.current_user_roles == ["editor"]
                assert svc.current_user_permissions == ["read"]
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_failed_profile_does_not_cache(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/user/profile", payload=make_failed_response())
                with pytest.raises(DmartException):
                    await svc.get_profile()
                assert svc.current_user_roles == []
                assert svc.current_user_permissions == []


# ---------------------------------------------------------------------------
# Query / CSV / Spaces / Children
# ---------------------------------------------------------------------------
class TestQuery:
    @pytest.mark.asyncio
    async def test_query_managed(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/query", payload=make_success_response())
                q = QueryRequest(type=QueryType.search, space_name="s", subpath="/", search="")
                resp = await svc.query(q)
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_query_public_scope(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/public/query", payload=make_success_response())
                q = QueryRequest(type=QueryType.search, space_name="s", subpath="/", search="")
                resp = await svc.query(q, scope="public")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_csv(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/csv", payload=make_success_response())
                q = QueryRequest(type=QueryType.search, space_name="s", subpath="/", search="")
                resp = await svc.csv(q)
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_get_spaces(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/query", payload=make_success_response())
                resp = await svc.get_spaces()
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_get_children(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/query", payload=make_success_response())
                resp = await svc.get_children("myspace", "/docs", limit=5, offset=0)
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_get_children_with_types(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/query", payload=make_success_response())
                resp = await svc.get_children(
                    "myspace", "/", restrict_types=[ResourceType.content, ResourceType.folder],
                )
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# Space / Request (actions)
# ---------------------------------------------------------------------------
class TestActions:
    def _make_action(self) -> ActionRequest:
        return ActionRequest(
            space_name="myspace",
            request_type=RequestType.create,
            records=[ActionRequestRecord(
                resource_type=ResourceType.content,
                shortname="doc",
                subpath="/",
                attributes={"title": "New"},
            )],
        )

    @pytest.mark.asyncio
    async def test_space(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/space", payload=make_success_response())
                resp = await svc.space(self._make_action())
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_request(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/request", payload=make_success_response())
                resp = await svc.request(self._make_action())
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# retrieve_entry
# ---------------------------------------------------------------------------
class TestRetrieveEntry:
    @pytest.mark.asyncio
    async def test_success(self):
        url = f"{BASE_URL}/managed/entry/content/myspace/docs/doc1?retrieve_json_payload=False&retrieve_attachments=False&validate_schema=True"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(url, payload=make_entry_response())
                entry = await svc.retrieve_entry(
                    ResourceType.content, "myspace", "docs", "doc1",
                )
                assert isinstance(entry, ResponseEntry)
                assert entry.uuid == "abc-123"
                assert entry.shortname == "myentry"

    @pytest.mark.asyncio
    async def test_with_options(self):
        url = f"{BASE_URL}/public/entry/folder/sp/sub/sn?retrieve_json_payload=True&retrieve_attachments=True&validate_schema=False"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(url, payload=make_entry_response())
                entry = await svc.retrieve_entry(
                    ResourceType.folder, "sp", "sub", "sn",
                    retrieve_json_payload=True,
                    retrieve_attachments=True,
                    validate_schema=False,
                    scope="public",
                )
                assert isinstance(entry, ResponseEntry)

    @pytest.mark.asyncio
    async def test_failed_raises(self):
        url = f"{BASE_URL}/managed/entry/content/s/p/n?retrieve_json_payload=False&retrieve_attachments=False&validate_schema=True"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(url, payload=make_failed_response())
                with pytest.raises(DmartException):
                    await svc.retrieve_entry(ResourceType.content, "s", "p", "n")

    @pytest.mark.asyncio
    async def test_client_error_raises(self):
        url = f"{BASE_URL}/managed/entry/content/s/p/n?retrieve_json_payload=False&retrieve_attachments=False&validate_schema=True"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(url, exception=aiohttp.ClientError("timeout"))
                with pytest.raises(DmartException) as exc_info:
                    await svc.retrieve_entry(ResourceType.content, "s", "p", "n")
                assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# upload_with_payload
# ---------------------------------------------------------------------------
class TestUploadWithPayload:
    @pytest.mark.asyncio
    async def test_basic_upload(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/resource_with_payload", payload=make_success_response())
                fake_file = io.BytesIO(b"file content")
                resp = await svc.upload_with_payload(
                    space_name="myspace",
                    subpath="/uploads",
                    shortname="file1",
                    resource_type=ResourceType.media,
                    payload_file=fake_file,
                )
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_upload_with_content_type_and_schema(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/resource_with_payload", payload=make_success_response())
                resp = await svc.upload_with_payload(
                    space_name="s",
                    subpath="/",
                    shortname="f",
                    resource_type=ResourceType.json,
                    payload_file=io.BytesIO(b"{}"),
                    content_type=ContentType.json,
                    schema_shortname="myschema",
                )
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# fetch_data_asset
# ---------------------------------------------------------------------------
class TestFetchDataAsset:
    @pytest.mark.asyncio
    async def test_basic(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/data-asset", payload=make_success_response())
                resp = await svc.fetch_data_asset(
                    resource_type="csv",
                    data_asset_type="csv",
                    space_name="data",
                    subpath="/assets",
                    shortname="sales",
                )
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_with_options(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/managed/data-asset", payload=make_success_response())
                resp = await svc.fetch_data_asset(
                    resource_type="parquet",
                    data_asset_type="parquet",
                    space_name="data",
                    subpath="/",
                    shortname="ds",
                    query_string="SELECT name FROM file",
                    filter_data_assets=["col1"],
                    branch_name="dev",
                )
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# get_attachment_url (sync, no HTTP)
# ---------------------------------------------------------------------------
class TestGetAttachmentUrl:
    def test_basic(self):
        svc = DmartService(BASE_URL)
        url = svc.get_attachment_url(
            ResourceType.media, "sp", "sub", "parent", "child",
        )
        assert url == f"{BASE_URL}/managed/payload/media/sp/sub/parent/child"

    def test_with_ext(self):
        svc = DmartService(BASE_URL)
        url = svc.get_attachment_url(
            ResourceType.media, "sp", "sub", "parent", "child", ext=".png",
        )
        assert url.endswith("/child.png")

    def test_custom_scope(self):
        svc = DmartService(BASE_URL)
        url = svc.get_attachment_url(
            ResourceType.media, "sp", "sub", "p", "c", scope="public",
        )
        assert "/public/payload/" in url


# ---------------------------------------------------------------------------
# get_space_health / get_payload
# ---------------------------------------------------------------------------
class TestMiscEndpoints:
    @pytest.mark.asyncio
    async def test_get_space_health(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/managed/health/myspace", payload=make_success_response())
                resp = await svc.get_space_health("myspace")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_get_payload(self):
        url = f"{BASE_URL}/managed/payload/content/sp/sub/doc.json"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(url, payload=make_success_response())
                resp = await svc.get_payload("content", "sp", "sub", "doc")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_get_payload_with_schema(self):
        url = f"{BASE_URL}/managed/payload/content/sp/sub/doc_article.json"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(url, payload=make_success_response())
                resp = await svc.get_payload("content", "sp", "sub", "doc", schema_shortname="_article")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_get_manifest(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/info/manifest", payload=make_success_response())
                resp = await svc.get_manifest()
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_get_settings(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.get(f"{BASE_URL}/info/settings", payload=make_success_response())
                resp = await svc.get_settings()
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# progress_ticket
# ---------------------------------------------------------------------------
class TestProgressTicket:
    @pytest.mark.asyncio
    async def test_basic(self):
        url = f"{BASE_URL}/managed/progress-ticket/sp/sub/t1/approve"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.put(url, payload=make_success_response())
                resp = await svc.progress_ticket("sp", "sub", "t1", "approve")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_with_resolution_and_comment(self):
        url = f"{BASE_URL}/managed/progress-ticket/sp/sub/t1/resolve"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.put(url, payload=make_success_response())
                resp = await svc.progress_ticket(
                    "sp", "sub", "t1", "resolve",
                    resolution="fixed", comment="done",
                )
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# submit
# ---------------------------------------------------------------------------
class TestSubmit:
    @pytest.mark.asyncio
    async def test_basic(self):
        url = f"{BASE_URL}/public/submit/sp/article/sub"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(url, payload=make_success_response())
                resp = await svc.submit("sp", "article", "sub", {"title": "hi"})
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_with_resource_type(self):
        url = f"{BASE_URL}/public/submit/sp/content/article/sub"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(url, payload=make_success_response())
                resp = await svc.submit(
                    "sp", "article", "sub", {"title": "hi"},
                    resource_type=ResourceType.content,
                )
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_with_workflow(self):
        url = f"{BASE_URL}/public/submit/sp/content/review/article/sub"
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(url, payload=make_success_response())
                resp = await svc.submit(
                    "sp", "article", "sub", {},
                    resource_type=ResourceType.content,
                    workflow_shortname="review",
                )
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# OTP / Password endpoints
# ---------------------------------------------------------------------------
class TestOtp:
    @pytest.mark.asyncio
    async def test_otp_request_msisdn(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/otp-request", payload=make_success_response())
                resp = await svc.otp_request(msisdn="+123456789")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_otp_request_email(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/otp-request", payload=make_success_response())
                resp = await svc.otp_request(email="a@b.com")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_otp_request_with_language(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/otp-request", payload=make_success_response())
                resp = await svc.otp_request(email="a@b.com", accept_language="ar")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_otp_request_login(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/otp-request-login", payload=make_success_response())
                resp = await svc.otp_request_login(msisdn="+123")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_otp_request_login_with_language(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/otp-request-login", payload=make_success_response())
                resp = await svc.otp_request_login(email="x@y.com", accept_language="en")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_confirm_otp(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/otp-confirm", payload=make_success_response())
                resp = await svc.confirm_otp("123456", msisdn="+123")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_confirm_otp_email(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/otp-confirm", payload=make_success_response())
                resp = await svc.confirm_otp("654321", email="a@b.com")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_password_reset_request(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/password-reset-request", payload=make_success_response())
                resp = await svc.password_reset_request(email="a@b.com")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_password_reset_request_msisdn(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/password-reset-request", payload=make_success_response())
                resp = await svc.password_reset_request(msisdn="+111")
                assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_password_reset_request_shortname(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(f"{BASE_URL}/user/password-reset-request", payload=make_success_response())
                resp = await svc.password_reset_request(shortname="user1")
                assert resp.status == "success"


# ---------------------------------------------------------------------------
# Lazy session creation via _get_session
# ---------------------------------------------------------------------------
class TestLazySession:
    @pytest.mark.asyncio
    async def test_request_creates_session_lazily(self):
        svc = DmartService(BASE_URL)
        assert svc._session is None
        with aioresponses() as m:
            m.get(f"{BASE_URL}/info/manifest", payload=make_success_response())
            await svc.get_manifest()
        assert svc._session is not None
        await svc.close()
