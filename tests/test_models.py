"""Tests for pydmart.models."""

import pytest
from pydantic import ValidationError
from pydmart.models import (
    Error,
    DmartException,
    ApiResponseRecord,
    ApiResponse,
    Translation,
    LoginResponseRecord,
    Permission,
    ProfileResponseRecord,
    AggregationReducer,
    AggregationType,
    QueryRequest,
    JoinQuery,
    Payload,
    MetaExtended,
    ResponseEntry,
    ResponseRecord,
    ActionResponse,
    ActionRequestRecord,
    ActionRequest,
)
from pydmart.enums import (
    Status,
    QueryType,
    JoinType,
    SortType,
    ResourceType,
    RequestType,
    ContentType,
)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------
class TestError:
    def test_basic(self):
        err = Error(type="auth", code=401, message="unauthorized")
        assert err.type == "auth"
        assert err.code == 401
        assert err.message == "unauthorized"
        assert err.info is None

    def test_with_info(self):
        err = Error(type="validation", code=422, message="bad", info=[{"field": "name"}])
        assert err.info == [{"field": "name"}]

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            Error(type="x", code=1)  # missing message


# ---------------------------------------------------------------------------
# DmartException
# ---------------------------------------------------------------------------
class TestDmartException:
    def test_is_exception(self):
        err = Error(type="x", code=1, message="m")
        exc = DmartException(status_code=400, error=err)
        assert isinstance(exc, Exception)
        assert exc.status_code == 400
        assert exc.error is err

    def test_raise_and_catch(self):
        err = Error(type="x", code=1, message="m")
        with pytest.raises(DmartException) as exc_info:
            raise DmartException(status_code=500, error=err)
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# ApiResponseRecord
# ---------------------------------------------------------------------------
class TestApiResponseRecord:
    def test_basic(self):
        rec = ApiResponseRecord(
            resource_type="content",
            shortname="doc1",
            subpath="/docs",
            attributes={"title": "Hello"},
        )
        assert rec.resource_type == "content"
        assert rec.shortname == "doc1"
        assert rec.attachments is None

    def test_with_attachments(self):
        rec = ApiResponseRecord(
            resource_type="content",
            shortname="doc1",
            subpath="/",
            attributes={},
            attachments={"media": []},
        )
        assert rec.attachments == {"media": []}


# ---------------------------------------------------------------------------
# ApiResponse
# ---------------------------------------------------------------------------
class TestApiResponse:
    def test_success_empty(self):
        resp = ApiResponse(status=Status.success)
        assert resp.status == Status.success
        assert resp.records == []
        assert resp.error is None

    def test_success_with_records(self):
        resp = ApiResponse(
            status=Status.success,
            records=[{
                "resource_type": "user",
                "shortname": "admin",
                "subpath": "/",
                "attributes": {"role": "admin"},
            }],
        )
        assert len(resp.records) == 1
        assert resp.records[0].shortname == "admin"

    def test_failed_with_error(self):
        resp = ApiResponse(
            status=Status.failed,
            error=Error(type="auth", code=401, message="nope"),
        )
        assert resp.status == Status.failed
        assert resp.error.code == 401

    def test_extra_fields_allowed(self):
        resp = ApiResponse(status=Status.success, custom_field="hello")
        assert resp.status == Status.success

    def test_missing_status_raises(self):
        with pytest.raises(ValidationError):
            ApiResponse()


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------
class TestTranslation:
    def test_all_none(self):
        t = Translation()
        assert t.en is None and t.ar is None and t.ku is None

    def test_partial(self):
        t = Translation(en="Hello", ar="\u0645\u0631\u062d\u0628\u0627")
        assert t.en == "Hello"
        assert t.ku is None


# ---------------------------------------------------------------------------
# LoginResponseRecord / ProfileResponseRecord
# ---------------------------------------------------------------------------
class TestLoginResponseRecord:
    def test_inherits_api_record(self):
        rec = LoginResponseRecord(
            resource_type="user", shortname="u", subpath="/", attributes={"access_token": "tok"}
        )
        assert isinstance(rec, ApiResponseRecord)
        assert rec.attributes["access_token"] == "tok"


class TestProfileResponseRecord:
    def test_inherits_api_record(self):
        rec = ProfileResponseRecord(
            resource_type="user", shortname="u", subpath="/", attributes={"roles": []}
        )
        assert isinstance(rec, ApiResponseRecord)


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------
class TestPermission:
    def test_basic(self):
        p = Permission(allowed_fields_values={"status": ["active"]})
        assert p.allowed_actions == []
        assert p.conditions == []
        assert p.restricted_fields == []
        assert p.allowed_fields_values == {"status": ["active"]}


# ---------------------------------------------------------------------------
# AggregationReducer / AggregationType
# ---------------------------------------------------------------------------
class TestAggregationReducer:
    def test_basic(self):
        r = AggregationReducer(name="count", alias="cnt")
        assert r.name == "count"
        assert r.args == []


class TestAggregationType:
    def test_with_reducer_objects(self):
        agg = AggregationType(
            load=["field1"],
            group_by=["field2"],
            reducers=[AggregationReducer(name="sum", alias="total", args=["amount"])],
        )
        assert len(agg.reducers) == 1

    def test_with_string_reducers(self):
        agg = AggregationType(reducers=["count", "sum"])
        assert agg.reducers == ["count", "sum"]


# ---------------------------------------------------------------------------
# QueryRequest
# ---------------------------------------------------------------------------
class TestQueryRequest:
    def test_minimal(self):
        q = QueryRequest(type=QueryType.search, space_name="data", subpath="/", search="hello")
        assert q.type == QueryType.search
        assert q.limit == 10
        assert q.offset == 0
        assert q.sort_type == SortType.ascending

    def test_full(self):
        q = QueryRequest(
            type=QueryType.aggregation,
            space_name="data",
            subpath="/reports",
            search="*",
            filter_types=[ResourceType.content],
            filter_schema_names=["article"],
            filter_shortnames=["doc1"],
            from_date="2024-01-01",
            to_date="2024-12-31",
            sort_by="created_at",
            sort_type=SortType.descending,
            retrieve_json_payload=True,
            retrieve_attachments=True,
            validate_schema=False,
            jq_filter=".body",
            exact_subpath=True,
            limit=50,
            offset=10,
            aggregation_data=AggregationType(reducers=["count"]),
            join=[JoinQuery(join_on="payload.body.author:shortname", alias="author", type=JoinType.left)],
        )
        assert q.filter_types == [ResourceType.content]
        assert q.limit == 50
        assert q.aggregation_data is not None
        assert q.join is not None and q.join[0].alias == "author"

    def test_model_dump_roundtrip(self):
        q = QueryRequest(type=QueryType.search, space_name="s", subpath="/", search="")
        d = q.model_dump()
        assert d["type"] == "search"
        q2 = QueryRequest(**d)
        assert q2 == q

    def test_join_defaults_none(self):
        q = QueryRequest(type=QueryType.search, space_name="s", subpath="/", search="")
        assert q.join is None
        # the client sends an explicit null (not a dropped key) when no join is set
        assert q.model_dump()["join"] is None

    def test_with_join(self):
        sub = QueryRequest(
            type=QueryType.subpath, space_name="shop", subpath="customers",
            search="", retrieve_json_payload=True,
        )
        q = QueryRequest(
            type=QueryType.subpath, space_name="shop", subpath="orders",
            search="", retrieve_json_payload=True,
            join=[JoinQuery(join_on="payload.body.customer:shortname", alias="customer", query=sub)],
        )
        assert q.join is not None
        assert len(q.join) == 1
        assert q.join[0].alias == "customer"
        assert isinstance(q.join[0].query, QueryRequest)

    def test_join_serializes_in_model_dump(self):
        sub = QueryRequest(
            type=QueryType.subpath, space_name="shop", subpath="customers", search="",
        )
        q = QueryRequest(
            type=QueryType.subpath, space_name="shop", subpath="orders", search="",
            join=[JoinQuery(join_on="payload.body.customer:shortname", alias="customer", query=sub)],
        )
        d = q.model_dump()
        assert isinstance(d["join"], list)
        assert d["join"][0]["join_on"] == "payload.body.customer:shortname"
        assert d["join"][0]["alias"] == "customer"
        # omitted type => null on the wire; the server treats null/absent as a left join
        assert d["join"][0]["type"] is None
        assert d["join"][0]["query"]["subpath"] == "customers"
        # roundtrip preserves the join
        q2 = QueryRequest(**d)
        assert q2 == q


# ---------------------------------------------------------------------------
# JoinType
# ---------------------------------------------------------------------------
class TestJoinType:
    def test_values(self):
        assert JoinType.left == "left"
        assert JoinType.right == "right"
        assert JoinType.inner == "inner"
        assert JoinType.outer == "outer"


# ---------------------------------------------------------------------------
# JoinQuery
# ---------------------------------------------------------------------------
class TestJoinQuery:
    def test_minimal(self):
        j = JoinQuery(join_on="payload.body.customer:shortname", alias="customer")
        assert j.join_on == "payload.body.customer:shortname"
        assert j.alias == "customer"
        # null/absent type => backend treats as a left join
        assert j.type is None
        assert j.query is None

    def test_with_type(self):
        j = JoinQuery(join_on="a:b", alias="x", type=JoinType.inner)
        assert j.type == JoinType.inner

    def test_nested_query_is_queryrequest(self):
        sub = QueryRequest(type=QueryType.subpath, space_name="shop", subpath="customers", search="")
        j = JoinQuery(join_on="payload.body.customer:shortname", alias="customer", query=sub)
        assert isinstance(j.query, QueryRequest)
        assert j.query.subpath == "customers"

    def test_model_dump_snake_case(self):
        sub = QueryRequest(type=QueryType.subpath, space_name="shop", subpath="customers", search="")
        j = JoinQuery(
            join_on="payload.body.customer:shortname", alias="customer",
            query=sub, type=JoinType.left,
        )
        d = j.model_dump()
        assert {"join_on", "alias", "query", "type"}.issubset(d.keys())
        assert d["join_on"] == "payload.body.customer:shortname"
        assert d["alias"] == "customer"
        assert d["type"] == "left"
        assert isinstance(d["query"], dict)
        assert d["query"]["subpath"] == "customers"
        assert d["query"]["type"] == "subpath"

    def test_roundtrip(self):
        sub = QueryRequest(type=QueryType.subpath, space_name="shop", subpath="customers", search="")
        j = JoinQuery(join_on="a:b", alias="x", query=sub, type=JoinType.outer)
        j2 = JoinQuery(**j.model_dump())
        assert j2 == j

    def test_multi_pair_join_on_survives_serialization(self):
        # comma-separated multi-pair join_on and the trailing "[]" array hint are
        # passed through verbatim by the client (the server parses them).
        val = "payload.body.a:shortname,payload.body.b[]:subpath"
        j = JoinQuery(join_on=val, alias="multi")
        d = j.model_dump()
        assert d["join_on"] == val
        assert JoinQuery(**d).join_on == val
        # also survives nested inside a QueryRequest.join
        q = QueryRequest(type=QueryType.search, space_name="s", subpath="/p", search="", join=[j])
        assert q.model_dump()["join"][0]["join_on"] == val


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------
class TestPayload:
    def test_basic(self):
        p = Payload(content_type=ContentType.json, body={"key": "value"})
        assert p.content_type == ContentType.json
        assert p.body == {"key": "value"}

    def test_string_body(self):
        p = Payload(content_type=ContentType.text, body="plain text")
        assert p.body == "plain text"


# ---------------------------------------------------------------------------
# MetaExtended
# ---------------------------------------------------------------------------
class TestMetaExtended:
    def test_all_none_defaults(self):
        m = MetaExtended()
        assert m.email is None
        assert m.msisdn is None
        assert m.is_email_verified is None
        assert m.state is None

    def test_partial(self):
        m = MetaExtended(email="a@b.com", state="active")
        assert m.email == "a@b.com"
        assert m.state == "active"


# ---------------------------------------------------------------------------
# ResponseEntry
# ---------------------------------------------------------------------------
class TestResponseEntry:
    def test_minimal(self):
        entry = ResponseEntry(uuid="u1", is_active=True, tags={"a", "b"})
        assert entry.uuid == "u1"
        assert entry.shortname is None
        assert entry.subpath is None
        assert entry.is_active is True
        assert "a" in entry.tags

    def test_full(self):
        entry = ResponseEntry(
            uuid="u1",
            shortname="entry1",
            subpath="/content",
            is_active=False,
            tags=set(),
            displayname=Translation(en="Entry One"),
            created_at="2024-01-01T00:00:00Z",
            owner_shortname="admin",
            email="a@b.com",
            payload=Payload(content_type=ContentType.json, body={}),
        )
        assert entry.shortname == "entry1"
        assert entry.displayname.en == "Entry One"
        assert entry.payload.content_type == ContentType.json

    def test_inherits_meta_extended(self):
        assert issubclass(ResponseEntry, MetaExtended)


# ---------------------------------------------------------------------------
# ResponseRecord
# ---------------------------------------------------------------------------
class TestResponseRecord:
    def test_basic(self):
        rec = ResponseRecord(
            resource_type=ResourceType.content,
            uuid="u1",
            shortname="doc",
            subpath="/",
            attributes={"status": "ok"},
        )
        assert rec.resource_type == ResourceType.content
        assert rec.uuid == "u1"


# ---------------------------------------------------------------------------
# ActionResponse
# ---------------------------------------------------------------------------
class TestActionResponse:
    def test_success_empty(self):
        resp = ActionResponse(status=Status.success)
        assert resp.records == []

    def test_with_records(self):
        resp = ActionResponse(
            status=Status.success,
            records=[{
                "resource_type": "content",
                "uuid": "u1",
                "shortname": "doc",
                "subpath": "/",
                "attributes": {},
            }],
        )
        assert len(resp.records) == 1


# ---------------------------------------------------------------------------
# ActionRequestRecord
# ---------------------------------------------------------------------------
class TestActionRequestRecord:
    def test_basic(self):
        rec = ActionRequestRecord(
            resource_type=ResourceType.content,
            shortname="newdoc",
            subpath="/docs",
            attributes={"title": "New"},
        )
        assert rec.uuid is None
        assert rec.attachments is None

    def test_with_uuid(self):
        rec = ActionRequestRecord(
            resource_type=ResourceType.content,
            uuid="u1",
            shortname="doc",
            subpath="/",
            attributes={},
        )
        assert rec.uuid == "u1"


# ---------------------------------------------------------------------------
# ActionRequest
# ---------------------------------------------------------------------------
class TestActionRequest:
    def test_basic(self):
        req = ActionRequest(
            space_name="myspace",
            request_type=RequestType.create,
        )
        assert req.records == []

    def test_with_records(self):
        rec = ActionRequestRecord(
            resource_type=ResourceType.content,
            shortname="doc",
            subpath="/",
            attributes={},
        )
        req = ActionRequest(
            space_name="myspace",
            request_type=RequestType.create,
            records=[rec],
        )
        assert len(req.records) == 1

    def test_model_dump(self):
        req = ActionRequest(
            space_name="s",
            request_type=RequestType.update,
        )
        d = req.model_dump()
        assert d["space_name"] == "s"
        assert d["request_type"] == "update"
