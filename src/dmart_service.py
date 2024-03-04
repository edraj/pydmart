from io import BytesIO
import json
import aiohttp
from enums import ResourceType, RequestType
from enum import Enum
from typing import Any, BinaryIO

class RequestMethod(str, Enum):
    get = "get"
    post = "post"
    delete = "delete"
    put = "put"
    patch = "patch"


class DmartService:
    
    def __init__(self, url, username: str, password: str) -> None:
        self.dmart_url = url
        self.username = username
        self.password = password
        
    async def connect(self):
        async with aiohttp.ClientSession() as session:
            json = {
                "shortname": self.username,
                "password": self.password,
            }
            response = await session.post(
                url=f"{self.dmart_url}/user/login",
                headers={"Content-Type": "application/json"},
                json=json,
            )
            resp_json = await response.json()
            if (
                resp_json.get("status", "failed") == "failed"
                or not resp_json.get("records")
            ):
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
            
    async def login(self, username: str, password: str) -> None:
        async with aiohttp.ClientSession() as session:
            json = {
                "shortname": username,
                "password": password,
            }
            url = f"{self.dmart_url}/user/login"
            response = await session.post(
                url,
                headers=self.json_headers,
                json=json,
            )
            resp_json = await response.json()
            if (
                (resp_json["status"] == "failed"
                and resp_json["error"]["type"] == "jwtauth")
                or not resp_json.get("records")
            ):
                return 

            print(f"\n\n {resp_json = } \n\n")
            self.auth_token = resp_json["records"][0]["attributes"]["access_token"]

    async def logout(self) -> None:
        await self.__api(
            endpoint="/user/logout",
            method=RequestMethod.post
        )
        self.auth_token = None
        
    async def get_profile(self) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
        if not self.auth_token:
            raise Exception("Not authenticated Dmart user")

        resp_json: dict[str, Any] = {}
        response: aiohttp.ClientResponse | None = None
        async with aiohttp.ClientSession() as session:
            response = await session.request(
                method.value,
                f"{self.dmart_url}{endpoint}",
                headers=self.json_headers if json else self.headers,
                json=json if not data else None,
                data=data if data else None,
            )
            resp_json = await response.json()

        if response is None or response.status != 200:
            raise Exception(f"dmart_error: {resp_json.get("error", {}).get("message", "")} AT {endpoint}")

        return resp_json

    async def __request(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        request_type: RequestType,
        attributes: dict[str, Any] = {},
        resource_type: ResourceType = ResourceType.content,
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
        return await self.__api(
            (
                f"/managed/entry/{resource_type}/{space_name}/{subpath}/{shortname}"
                f"?retrieve_json_payload=true&retrieve_attachments={retrieve_attachments}"
            ),
            RequestMethod.get,
        )

    async def read_json_payload(
        self, space_name: str, subpath: str, shortname: str
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
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


