from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, ConfigDict, Field

from .enums import ContentType, ResourceType, QueryType, SortType, Status, RequestType


class Error(BaseModel):
    type: str
    code: int
    message: str
    info: list[dict] | None = None


class DmartException(Exception):
    status_code: int
    error: Error

    def __init__(self, status_code: int, error: Error):
        super().__init__(error)
        self.status_code = status_code
        self.error = error


class ApiResponseRecord(BaseModel):
    resource_type: str
    shortname: str
    subpath: str
    attributes: Dict[str, Any]
    attachments: Optional[Dict[str, Any]] = None


class ApiResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    status: Status
    error: Optional[Error] = None
    records: List[ApiResponseRecord] = Field(default=[])


class Translation(BaseModel):
    en: str | None = None
    ar: str | None = None
    ku: str | None = None


class LoginResponseRecord(ApiResponseRecord):
    attributes: Dict[str, Any]


class Permission(BaseModel):
    allowed_actions: List[str] = []
    conditions: List[str] = []
    restricted_fields: List[Any] = []
    allowed_fields_values: Dict[str, Any]


class ProfileResponseRecord(ApiResponseRecord):
    attributes: Dict[str, Any]


class AggregationReducer(BaseModel):
    name: str
    alias: str
    args: List[str] = []


class AggregationType(BaseModel):
    load: List[str] = []
    group_by: List[str] = []
    reducers: Union[List[AggregationReducer], List[str]]


class QueryRequest(BaseModel):
    type: QueryType
    space_name: str
    subpath: str
    filter_types: Optional[List[ResourceType]] = []
    filter_schema_names: Optional[List[str]] = []
    filter_shortnames: Optional[List[str]] = []
    search: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    sort_by: Optional[str] = None
    sort_type: Optional[SortType] = SortType.ascending
    retrieve_json_payload: Optional[bool] = False
    retrieve_attachments: Optional[bool] = False
    validate_schema: Optional[bool] = True
    jq_filter: Optional[str] = None
    exact_subpath: Optional[bool] = False
    limit: Optional[int] = 10
    offset: Optional[int] = 0
    aggregation_data: Optional[AggregationType] = None


class Payload(BaseModel):
    content_type: ContentType
    schema_shortname: Optional[str] = None
    checksum: Optional[str] = None
    body: Optional[Union[str, Dict[str, Any], Any]] = None
    last_validated: Optional[str] = None
    validation_status: Optional[str] = None


class MetaExtended(BaseModel):
    email: Optional[str] = None
    msisdn: Optional[str] = None
    is_email_verified: Optional[bool] = None
    is_msisdn_verified: Optional[bool] = None
    force_password_change: Optional[bool] = None
    password: Optional[str] = None
    workflow_shortname: Optional[str] = None
    state: Optional[str] = None
    is_open: Optional[bool] = None


class ResponseEntry(MetaExtended):
    uuid: str
    shortname: str = None
    subpath: str = None
    is_active: bool
    displayname: Optional[Translation] = None
    description: Optional[Translation] = None
    tags: Set[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    owner_shortname: Optional[str] = None
    payload: Optional[Payload] = None
    relationships: Optional[Any] = None
    attachments: Optional[Dict[str, Any]] = None


class ResponseRecord(BaseModel):
    resource_type: ResourceType
    uuid: str
    shortname: str
    subpath: str
    attributes: Dict[str, Any]


class ActionResponse(BaseModel):
    status: Status
    error: Optional[Error] = None
    records: List[ResponseRecord] = []


class ActionRequestRecord(BaseModel):
    resource_type: ResourceType
    uuid: Optional[str] = None
    shortname: str
    subpath: str
    attributes: Dict[str, Any]
    attachments: Optional[Dict[ResourceType, List[Any]]] = None


class ActionRequest(BaseModel):
    space_name: str
    request_type: RequestType
    records: List[ActionRequestRecord] = []
