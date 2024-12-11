from io import BytesIO
import json
import aiohttp
from enum import StrEnum
from typing import Any, BinaryIO
from pydantic import BaseModel, Field
from pydantic.types import UUID4 as UUID

SUBPATH = "^[a-zA-Z\u0621-\u064A0-9\u0660-\u0669_/]{1,128}$"
SHORTNAME = "^[a-zA-Z\u0621-\u064A0-9\u0660-\u0669_]{1,64}$"

class Status(StrEnum):
    success = "success"
    failed = "failed"
    
class RequestType(StrEnum):
    create = "create"
    update = "update"
    patch = "patch"
    update_acl = "update_acl"
    assign = "assign"
    r_replace = "replace"
    delete = "delete"
    move = "move"

    
class ResourceType(StrEnum):
    user = "user"
    group = "group"
    folder = "folder"
    schema = "schema"
    content = "content"
    acl = "acl"
    comment = "comment"
    media = "media"
    data_asset = "data_asset"
    locator = "locator"
    relationship = "relationship"
    alteration = "alteration"
    history = "history"
    space = "space"
    branch = "branch"
    permission = "permission"
    role = "role"
    ticket = "ticket"
    json = "json"
    lock = "lock"
    post = "post"
    reaction = "reaction"
    reply = "reply"
    share = "share"
    plugin_wrapper = "plugin_wrapper"
    notification = "notification"
    csv = "csv"
    jsonl = "jsonl"
    sqlite = "sqlite"
    duckdb = "duckdb"
    parquet = "parquet"
    
class RequestMethod(StrEnum):
    get = "get"
    post = "post"
    delete = "delete"
    put = "put"
    patch = "patch"

class Error(BaseModel):
    type: str
    code: int
    message: str
    info: list[dict] | None = None

class DmartException(Exception):
    status_code: int
    error: Error

    def __init__(self, status_code: int, error: Error):
        super().__init__(status_code)
        self.status_code = status_code
        self.error = error

class Record(BaseModel):
    resource_type: ResourceType
    uuid: UUID | None = None
    shortname: str = Field(pattern=SHORTNAME)
    subpath: str = Field(pattern=SUBPATH)
    attributes: dict[str, Any]
    attachments: dict[ResourceType, list[Any]] | None = None
    retrieve_lock_status: bool = False

    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        if self.subpath != "/":
            self.subpath = self.subpath.strip("/")

class DmartResponse(BaseModel):
    status: Status
    error: Error | None = None
    records: list[Record] | Any | None = None
    attributes: dict[str, Any] | None = None

class DmartService:
    
    @classmethod
    async def create_session_pool(cls):
        if not cls.session:
            cls.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector())


    async def __init__(self, url: str, username: str, password: str) -> None:
        self.dmart_url = url
        self.username = username
        self.password = password
        await self.create_session_pool()

        
    async def connect(self):
        json = {
            "shortname": self.username,
            "password": self.password,
        }
        async with self.session.post(url=f"{self.dmart_url}/user/login", headers={"Content-Type": "application/json"}, json=json) as response:
            resp_json = await response.json()
            if (resp_json.get("status", "failed") == "failed" or not resp_json.get("records")):
                raise ConnectionError("Failed to connect to the Dmart instance, invalid url or credentials") 

            self.auth_token = resp_json["records"][0]["attributes"]["access_token"]


    @property
    def json_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
        }

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.auth_token}",
        }
            
    # async def login(self, username: str, password: str) -> None:
    #     json = {
    #         "shortname": username,
    #         "password": password,
    #     }
    #     async with aiohttp.ClientSession() as session:
    #         url = f"{self.dmart_url}/user/login"
    #         response = await session.post(
    #             url,
    #             headers=self.json_headers,
    #             json=json,
    #         )
    #         resp_json = await response.json()
    #         if (
    #             (resp_json["status"] == "failed"
    #             and resp_json["error"]["type"] == "jwtauth")
    #             or not resp_json.get("records")
    #         ):
    #             return 
    #
    #         print(f"\n\n {resp_json = } \n\n")
    #         self.auth_token = resp_json["records"][0]["attributes"]["access_token"]

    async def disconnect(self) -> None:
        await self.__api(
            endpoint="/user/logout",
            method=RequestMethod.post
        )
        self.auth_token = None
        
    async def get_profile(self) -> DmartResponse:
        return await self.__api(
            endpoint="/user/profile",
            method=RequestMethod.get
        )
    
    async def __api(
        self,
        endpoint: str,
        method: RequestMethod,
        json: dict[str, Any] | None = None,
        data: aiohttp.FormData | None = None,
    ) -> DmartResponse:
        if not self.auth_token:
            raise DmartException(status_code=401, error=Error(code=10, type="login", message="Not authenticated Dmart user"))

        async with self.session.request(method.value, f"{self.dmart_url}{endpoint}", headers=self.json_headers if json else self.headers, json=json, data=data) as response:
            resp_json = await response.json()
            if response is None or response.status != 200:
                raise DmartException(
                    status_code = response.status,
                    error = Error.model_validate(resp_json["error"])
                )

            return DmartResponse.model_validate(response) 

    async def __request(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        request_type: RequestType,
        attributes: dict[str, Any] = {},
        resource_type: ResourceType = ResourceType.content,
    ) -> DmartResponse:
        return await self.__api(
            "/managed/request",
            RequestMethod.post,
            {
                "space_name": space_name,
                "request_type": request_type,
                "records": [
                    {
                        "resource_type": resource_type,
                        "subpath": subpath,
                        "shortname": shortname,
                        "attributes": attributes,
                    }
                ],
            },
        )

    async def create(
        self,
        space_name: str,
        subpath: str,
        attributes: dict[str, Any],
        shortname: str = "auto",
        resource_type: ResourceType = ResourceType.content,
    ) -> DmartResponse:
        return await self.__request(
            space_name,
            subpath,
            shortname,
            RequestType.create,
            attributes,
            resource_type,
        )

    async def upload_resource_with_payload(
        self,
        space_name: str,
        record: dict[str, Any],
        payload: BinaryIO,
        payload_file_name: str,
        payload_mime_type: str,
    ):
        record_file = BytesIO(bytes(json.dumps(record), "utf-8"))

        data = aiohttp.FormData()
        data.add_field(
            "request_record",
            record_file,
            filename="record.json",
            content_type="application/json",
        )
        data.add_field(
            "payload_file",
            payload,
            filename=payload_file_name,
            content_type=payload_mime_type,
        )
        data.add_field("space_name", space_name)

        return await self.__api(
            endpoint="/managed/resource_with_payload",
            method=RequestMethod.post,
            data=data,
        )

    async def query_data_asset(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        data_asset_type: str,
        query_string: str,
        schema_shortname: str | None = None,
        resource_type: ResourceType = ResourceType.content,
    ) -> DmartResponse:
        return await self.__api(
            "/managed/data-asset",
            RequestMethod.post,
            {
                "space_name": space_name,
                "subpath": subpath,
                "resource_type": resource_type,
                "shortname": shortname,
                "schema_shortname": schema_shortname,
                "data_asset_type": data_asset_type,
                "query_string": query_string
            },
        )
        
    async def read(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        retrieve_attachments: bool = False,
        resource_type: ResourceType = ResourceType.content,
    ) -> DmartResponse:
        return await self.__api(
            (
                f"/managed/entry/{resource_type}/{space_name}/{subpath}/{shortname}"
                f"?retrieve_json_payload=true&retrieve_attachments={retrieve_attachments}"
            ),
            RequestMethod.get,
        )

    async def read_json_payload(
        self, space_name: str, subpath: str, shortname: str
    ) -> DmartResponse:
        return await self.__api(
            f"/managed/payload/content/{space_name}/{subpath}/{shortname}.json",
            RequestMethod.get,
        )

    async def query(
        self,
        space_name: str,
        subpath: str,
        search: str = "",
        filter_schema_names: list[str] = [],
        **kwargs: Any,
    ) -> DmartResponse:
        return await self.__api(
            "/managed/query",
            RequestMethod.post,
            {
                "type": "search",
                "space_name": space_name,
                "subpath": subpath,
                "retrieve_json_payload": True,
                "filter_schema_names": filter_schema_names,
                "search": search,
                **kwargs,
            },
        )

    async def update(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        attributes: dict[str, Any],
        resource_type: ResourceType = ResourceType.content,
    ) -> DmartResponse:
        return await self.__request(
            space_name,
            subpath,
            shortname,
            RequestType.update,
            attributes,
            resource_type,
        )

    async def progress_ticket(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        action: str,
        cancellation_reasons: str | None = None,
    ) -> DmartResponse:
        request_body = None
        if cancellation_reasons:
            request_body = {"resolution": cancellation_reasons}
        return await self.__api(
            (f"/managed/progress-ticket/{space_name}/{subpath}/{shortname}/{action}"),
            RequestMethod.put,
            json=request_body,
        )

    async def delete(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        resource_type: ResourceType = ResourceType.content,
    ) -> DmartResponse:
        json: dict[str, Any] = {
            "space_name": space_name,
            "request_type": RequestType.delete,
            "records": [
                {
                    "resource_type": resource_type,
                    "subpath": subpath,
                    "shortname": shortname,
                    "attributes": {},
                }
            ],
        }
        return await self.__api("/managed/request", RequestMethod.post, json)

