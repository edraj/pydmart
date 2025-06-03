import json
import aiohttp
from typing import Any, Dict, List, Optional
from .models import (
    ApiResponse, ActionResponse, ResponseEntry, QueryRequest, ActionRequest,
    DmartException, Error
)
from .enums import QueryType, ResourceType, ContentType

class DmartService:
    base_url = "http://localhost:8282"
    current_user_roles = []
    current_user_permissions = []
    def __init__(self, base_url: str):
        self.base_url: str = base_url
        self.auth_token: str = ""

    @property
    def json_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}" if self.auth_token else "",
        }

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.auth_token}" if self.auth_token else "",
        }


    async def _request(self, method: str, url: str, **kwargs) -> Any:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    data = await response.json()
                    try:
                        return ApiResponse(**data)
                    except Exception as e:
                        print('Error:', data)
                        err = data.get('error', {
                            'type': 'request',
                            'code': 500,
                            'message': str(e)
                        })
                        error = Error(**err)
                        raise DmartException(status_code=400, error=error)
        except aiohttp.ClientResponseError as e:
            error = await e.response.json()
            raise DmartException(status_code=e.status, error=Error(**error))
        except aiohttp.ClientError as e:
            raise DmartException(status_code=500, error=Error(type="ClientError", code=500, message=str(e), info=[]))

    async def login(self, shortname: str, password: str) -> ApiResponse:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request("POST", f"{self.base_url}/user/login", json={"shortname": shortname, "password": password}) as response:
                    data = await response.json()
            if isinstance(data, dict):
                self.auth_token = data["records"][0]["attributes"]["access_token"]
                return ApiResponse(**data)
            else:
                raise DmartException(status_code=500, error=Error(type="ClientError", code=500, message="Invalid response", info=[]))
        except DmartException as e:
            raise e
        except aiohttp.ClientResponseError as e:
            error = await e.response.json()
            raise DmartException(status_code=e.status, error=Error(**error))
        except aiohttp.ClientError as e:
            raise DmartException(status_code=500, error=Error(type="ClientError", code=500, message=str(e), info=[]))

    async def login_by(self, credentials: Dict[str, Any], password: str) -> ApiResponse:
        data = await self._request("POST", f"{self.base_url}/user/login", json={**credentials, "password": password})
        self.auth_token = data["records"][0]["attributes"]["access_token"]
        return data

    async def logout(self) -> ApiResponse:
        return await self._request("POST", f"{self.base_url}/user/logout", headers=self.headers)

    async def create_user(self, request: Dict[str, Any]) -> ActionResponse:
        return await self._request("POST", f"{self.base_url}/user/create", json=request, headers=self.json_headers)

    async def update_user(self, request: Dict[str, Any]) -> ActionResponse:
        return await self._request("POST", f"{self.base_url}/user/profile", json=request, headers=self.json_headers)

    async def check_existing(self, prop: str, value: str) -> ResponseEntry:
        return await self._request("GET", f"{self.base_url}/user/check-existing?{prop}={value}", headers=self.headers)

    async def get_profile(self) -> ApiResponse:
        data = await self._request("GET", f"{self.base_url}/user/profile", headers=self.headers)
        if data.status == "success":
            self.current_user_permissions = data.records[0].attributes.get("permissions")
            self.current_user_roles = data.records[0].attributes.get("roles")
        return data

    async def query(self, query: QueryRequest, scope: str = "managed") -> ApiResponse:
        return await self._request("POST", f"{self.base_url}/{scope}/query", json=query.model_dump(), headers=self.json_headers)

    async def csv(self, query: QueryRequest) -> ApiResponse:
        return await self._request("POST", f"{self.base_url}/managed/csv", json=query.model_dump(), headers=self.json_headers)

    async def space(self, action: ActionRequest) -> ActionResponse:
        return await self._request("POST", f"{self.base_url}/managed/space", json=action.model_dump(), headers=self.json_headers)

    async def request(self, action: ActionRequest) -> ActionResponse:
        return await self._request("POST", f"{self.base_url}/managed/request", json=action.model_dump(), headers=self.json_headers)

    async def retrieve_entry(
        self,
        resource_type: ResourceType,
        space_name: str,
        subpath: str,
        shortname: str,
        retrieve_json_payload: bool = False,
        retrieve_attachments: bool = False,
        validate_schema: bool = True,
        scope: str = "managed"
    ) -> ResponseEntry:
        url = f"{scope}/entry/{resource_type}/{space_name}/{subpath}/{shortname}?retrieve_json_payload={retrieve_json_payload}&retrieve_attachments={retrieve_attachments}&validate_schema={validate_schema}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request("GET", f"{self.base_url}/{url}", headers=self.headers) as response:
                    data = await response.json()
                    return ResponseEntry(**data)
        except aiohttp.ClientResponseError as e:
            error = await e.response.json()
            raise DmartException(status_code=e.status, error=Error(**error))
        except aiohttp.ClientError as e:
            raise DmartException(status_code=500, error=Error(type="ClientError", code=500, message=str(e), info=[]))

    async def upload_with_payload(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        resource_type: ResourceType,
        payload_file: Any,
        content_type: Optional[ContentType] = None,
        schema_shortname: Optional[str] = None,
        scope: str = "managed"
    ) -> ApiResponse:
        request_record_body = {
            "resource_type": resource_type,
            "subpath": subpath,
            "shortname": shortname,
            "attributes": {"is_active": True, "payload": {"body": {}}},
        }
        if content_type:
            request_record_body["attributes"]["payload"]["content_type"] = content_type
        if schema_shortname:
            request_record_body["attributes"]["payload"]["schema_shortname"] = schema_shortname

        form_data = aiohttp.FormData()
        form_data.add_field("space_name", space_name)
        form_data.add_field("request_record", json.dumps(request_record_body), content_type="application/json")
        form_data.add_field("payload_file", payload_file)

        return await self._request("POST", f"{self.base_url}/{scope}/resource_with_payload", data=form_data, headers=self.headers)

    async def fetch_data_asset(
        self,
        resource_type: str,
        data_asset_type: str,
        space_name: str,
        subpath: str,
        shortname: str,
        query_string: str = "SELECT * FROM file",
        filter_data_assets: Optional[List[str]] = None,
        branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._request("POST", f"{self.base_url}/managed/data-asset", json={
            "space_name": space_name,
            "resource_type": resource_type,
            "data_asset_type": data_asset_type,
            "subpath": subpath,
            "shortname": shortname,
            "query_string": query_string,
            "filter_data_assets": filter_data_assets,
            "branch_name": branch_name,
        }, headers=self.json_headers)

    async def get_spaces(self) -> ApiResponse:
        return await self.query(QueryRequest(
            type=QueryType.spaces,
            space_name="management",
            subpath="/",
            search="",
            limit=100,
        ))

    async def get_children(
        self,
        space_name: str,
        subpath: str,
        limit: int = 20,
        offset: int = 0,
        restrict_types: Optional[List[ResourceType]] = None
    ) -> ApiResponse:
        return await self.query(QueryRequest(
            type=QueryType.search,
            space_name=space_name,
            subpath=subpath,
            filter_types=restrict_types,
            exact_subpath=True,
            search="",
            limit=limit,
            offset=offset,
        ))

    def get_attachment_url(
        self,
        resource_type: ResourceType,
        space_name: str,
        subpath: str,
        parent_shortname: str,
        shortname: str,
        ext: Optional[str] = None,
        scope: str = "managed"
    ) -> str:
        return f"{self.base_url}/{scope}/payload/{resource_type}/{space_name}/{subpath}/{parent_shortname}/{shortname}{ext or ''}"

    async def get_space_health(self, space_name: str) -> Dict[str, Any]:
        return await self._request("GET", f"{self.base_url}/managed/health/{space_name}", headers=self.headers)

    async def get_attachment_content(
        self,
        resource_type: str,
        space_name: str,
        subpath: str,
        shortname: str,
        scope: str = "managed"
    ) -> Dict[str, Any]:
        return await self._request("GET", f"{self.base_url}/{scope}/payload/{resource_type}/{space_name}/{subpath}/{shortname}", headers=self.headers)

    async def get_payload(
        self,
        resource_type: str,
        space_name: str,
        subpath: str,
        shortname: str,
        ext: str = ".json",
        scope: str = "managed"
    ) -> Dict[str, Any]:
        return await self._request("GET", f"{self.base_url}/{scope}/payload/{resource_type}/{space_name}/{subpath}/{shortname}{ext}", headers=self.headers)

    async def get_payload_content(
        self,
        resource_type: str,
        space_name: str,
        subpath: str,
        shortname: str,
        ext: str = ".json",
        scope: str = "managed"
    ) -> Dict[str, Any]:
        return await self._request("GET", f"{self.base_url}/{scope}/payload/{resource_type}/{space_name}/{subpath}/{shortname}{ext}", headers=self.headers)

    async def progress_ticket(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        action: str,
        resolution: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {}
        if resolution:
            payload["resolution"] = resolution
        if comment:
            payload["comment"] = comment

        return await self._request("PUT", f"{self.base_url}/managed/progress-ticket/{space_name}/{subpath}/{shortname}/{action}", json=payload, headers=self.json_headers)

    async def submit(
        self,
        space_name: str,
        schema_shortname: str,
        subpath: str,
        record: Dict[str, Any],
        resource_type: Optional[ResourceType] = None,
        workflow_shortname: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/public/submit/{space_name}"
        if resource_type:
            url += f"/{resource_type.value}"
        if workflow_shortname:
            url += f"/{workflow_shortname}"
        url += f"/{schema_shortname}/{subpath}"

        return await self._request("POST", url, json=record, headers=self.json_headers)

    async def get_manifest(self) -> Dict[str, Any]:
        return await self._request("GET", f"{self.base_url}/info/manifest", headers=self.headers)

    async def get_settings(self) -> Dict[str, Any]:
        return await self._request("GET", f"{self.base_url}/info/settings", headers=self.headers)