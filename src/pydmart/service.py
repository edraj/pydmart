import json
import aiohttp
from typing import Any, Dict, List, Optional
from .models import (
    ApiResponse, ActionResponse, ResponseEntry, QueryRequest, ActionRequest,
    DmartException, Error
)
from .enums import QueryType, ResourceType, ContentType

class DmartService:
    """High-level async client for the Dmart HTTP API.

    This service wraps the Dmart backend endpoints with convenient coroutine
    methods. Create a single instance per base_url and reuse it to keep the
    authentication token. Most methods return pydantic models that mirror the
    API responses.

    Attributes:
        base_url: Base endpoint of the Dmart service, e.g. https://api.example.com
        auth_token: Bearer token assigned upon successful login.
        current_user_roles: Cached roles from the user profile, if fetched.
        current_user_permissions: Cached permissions from the user profile, if fetched.
    """
    base_url = "http://localhost:8282"
    current_user_roles = []
    current_user_permissions = []
    def __init__(self, base_url: str):
        """Initialize the service.

        Args:
            base_url: Base URL of the Dmart API (without trailing slash).
        """
        self.base_url: str = base_url
        self.auth_token: str = ""

    @property
    def json_headers(self) -> Dict[str, str]:
        """HTTP headers including JSON content type and optional Authorization."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}" if self.auth_token else "",
        }

    @property
    def headers(self) -> Dict[str, str]:
        """HTTP headers including optional Authorization."""
        return {
            "Authorization": f"Bearer {self.auth_token}" if self.auth_token else "",
        }


    async def _request(self, method: str, url: str, **kwargs) -> Any:
        """Low-level request wrapper that normalizes responses and errors.

        Args:
            method: HTTP method (e.g., 'GET', 'POST').
            url: Fully qualified request URL.
            **kwargs: Passed through to aiohttp.ClientSession.request.

        Returns:
            ApiResponse or parsed model when possible; raises DmartException otherwise.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    data = await response.json()
                    try:
                        if data['status'] == 'failed':
                            raise DmartException(status_code=400, error=Error(**data['error']))
                        return ApiResponse(**data)
                    except Exception as e:
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
        """Login with shortname and password; stores auth token on success."""
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
        """Login with arbitrary credentials dict plus password; stores auth token."""
        data = await self._request("POST", f"{self.base_url}/user/login", json={**credentials, "password": password})
        self.auth_token = data["records"][0]["attributes"]["access_token"]
        return data

    async def logout(self) -> ApiResponse:
        """Invalidate current token server-side (if any)."""
        return await self._request("POST", f"{self.base_url}/user/logout", headers=self.headers)

    async def create_user(self, request: Dict[str, Any]) -> ActionResponse:
        """Create a new user.

        Args:
            request: Payload for the user creation endpoint.
        """
        return await self._request("POST", f"{self.base_url}/user/create", json=request, headers=self.json_headers)

    async def update_user(self, request: Dict[str, Any]) -> ActionResponse:
        """Update current user profile attributes.

        Args:
            request: Payload for the update endpoint.
        """
        return await self._request("POST", f"{self.base_url}/user/profile", json=request, headers=self.json_headers)

    async def check_existing(self, prop: str, value: str) -> ResponseEntry:
        """Check whether a user property already exists (e.g., email or shortname)."""
        return await self._request("GET", f"{self.base_url}/user/check-existing?{prop}={value}", headers=self.headers)

    async def get_profile(self) -> ApiResponse:
        """Fetch current user profile and cache permissions/roles on success."""
        data = await self._request("GET", f"{self.base_url}/user/profile", headers=self.headers)
        if data.status == "success":
            self.current_user_permissions = data.records[0].attributes.get("permissions")
            self.current_user_roles = data.records[0].attributes.get("roles")
        return data

    async def query(self, query: QueryRequest, scope: str = "managed") -> ApiResponse:
        """Run a query within a scope.

        Args:
            query: QueryRequest payload.
            scope: API scope, e.g. 'managed' or 'public'.
        """
        return await self._request("POST", f"{self.base_url}/{scope}/query", json=query.model_dump(), headers=self.json_headers)

    async def csv(self, query: QueryRequest) -> ApiResponse:
        """Export a query as CSV data (server-side generation)."""
        return await self._request("POST", f"{self.base_url}/managed/csv", json=query.model_dump(), headers=self.json_headers)

    # async def space(self, action: ActionRequest) -> ActionResponse:
    #     """Perform a space-level management action."""
    #     return await self._request("POST", f"{self.base_url}/managed/space", json=action.model_dump(), headers=self.json_headers)

    async def request(self, action: ActionRequest) -> ActionResponse:
        """Perform a generic managed request (create/update/etc.)."""
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
        """Retrieve a single entry with optional payload/attachments.

        Args:
            resource_type: Type of resource to fetch.
            space_name: Space identifier.
            subpath: Path within the space.
            shortname: Unique shortname of the entry.
            retrieve_json_payload: Whether to include JSON payload.
            retrieve_attachments: Whether to include attachments.
            validate_schema: Validate payload against its schema on server.
            scope: API scope.
        """
        url = f"{scope}/entry/{resource_type}/{space_name}/{subpath}/{shortname}?retrieve_json_payload={retrieve_json_payload}&retrieve_attachments={retrieve_attachments}&validate_schema={validate_schema}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request("GET", f"{self.base_url}/{url}", headers=self.headers) as response:
                    data = await response.json()
                    if data.get('status') == 'failed':
                        raise DmartException(status_code=400, error=Error(**data['error']))
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
        """Upload a file together with a JSON payload as a single request."""
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
        """Execute a query against a data asset (CSV/Parquet/JSONL/etc.)."""
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
        """List management spaces (up to limit)."""
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
        """List direct children of a subpath, optionally filtering by types."""
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
        """Build a direct URL to download an attachment payload."""
        return f"{self.base_url}/{scope}/payload/{resource_type}/{space_name}/{subpath}/{parent_shortname}/{shortname}{ext or ''}"

    async def get_space_health(self, space_name: str) -> Dict[str, Any]:
        """Get health information for a space."""
        return await self._request("GET", f"{self.base_url}/managed/health/{space_name}", headers=self.headers)

    async def get_payload(
        self,
        resource_type: str,
        space_name: str,
        subpath: str,
        shortname: str,
        schema_shortname: str = "",
        ext: str = ".json",
        scope: str = "managed"
    ) -> Dict[str, Any]:
        """Fetch raw payload for a resource.

        Args:
            resource_type: Resource type name.
            space_name: Space identifier.
            subpath: Path inside the space.
            shortname: Resource shortname.
            schema_shortname: Optional schema suffix to target specific variant.
            ext: Extension to fetch (default .json).
            scope: API scope.
        """
        return await self._request("GET", f"{self.base_url}/{scope}/payload/{resource_type}/{space_name}/{subpath}/{shortname}{schema_shortname}{ext}", headers=self.headers)

    async def progress_ticket(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        action: str,
        resolution: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Move a ticket through its workflow with optional resolution/comment."""
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
        """Public submit of a record to a space/schema, optionally via workflow."""
        url = f"{self.base_url}/public/submit/{space_name}"
        if resource_type:
            url += f"/{resource_type.value}"
        if workflow_shortname:
            url += f"/{workflow_shortname}"
        url += f"/{schema_shortname}/{subpath}"

        return await self._request("POST", url, json=record, headers=self.json_headers)

    async def otp_request(self, msisdn: Optional[str] = None, email: Optional[str] = None, accept_language: Optional[str] = None) -> ApiResponse:
        """Request an OTP for signup/verification via msisdn or email."""
        payload = {}
        if msisdn:
            payload["msisdn"] = msisdn
        if email:
            payload["email"] = email

        headers = self.json_headers
        if accept_language:
            headers["Accept-Language"] = accept_language

        return await self._request("POST", f"{self.base_url}/user/otp-request", json=payload, headers=headers)

    async def otp_request_login(self, msisdn: Optional[str] = None, email: Optional[str] = None, accept_language: Optional[str] = None) -> ApiResponse:
        """Request an OTP intended for login flows."""
        payload = {}
        if msisdn:
            payload["msisdn"] = msisdn
        if email:
            payload["email"] = email

        headers = self.json_headers
        if accept_language:
            headers["Accept-Language"] = accept_language

        return await self._request("POST", f"{self.base_url}/user/otp-request-login", json=payload, headers=headers)

    async def password_reset_request(self, msisdn: Optional[str] = None, shortname: Optional[str] = None, email: Optional[str] = None) -> ApiResponse:
        """Request a password reset token via msisdn, shortname, or email."""
        payload = {}
        if msisdn:
            payload["msisdn"] = msisdn
        if shortname:
            payload["shortname"] = shortname
        if email:
            payload["email"] = email

        return await self._request("POST", f"{self.base_url}/user/password-reset-request", json=payload, headers=self.json_headers)

    async def confirm_otp(self, otp: str, msisdn: Optional[str] = None, email: Optional[str] = None) -> ApiResponse:
        """Confirm an OTP code sent to msisdn or email."""
        payload = {
            "otp": otp
        }
        if msisdn:
            payload["msisdn"] = msisdn
        if email:
            payload["email"] = email

        return await self._request("POST", f"{self.base_url}/user/otp-confirm", json=payload, headers=self.json_headers)

    async def user_reset(self, shortname: str) -> ApiResponse:
        """Force-reset user status (admin action)."""
        return await self._request("POST", f"{self.base_url}/user/reset", json={"shortname": shortname}, headers=self.json_headers)

    async def validate_password(self, password: str) -> ApiResponse:
        """Validate password strength/policy server-side."""
        return await self._request("POST", f"{self.base_url}/user/validate_password", json={"password": password}, headers=self.json_headers)

    async def get_manifest(self) -> Dict[str, Any]:
        """Retrieve server manifest information.

        Returns:
            Dict containing version, build info and other manifest details.
        """
        return await self._request("GET", f"{self.base_url}/info/manifest", headers=self.headers)


async def get_settings(self) -> Dict[str, Any]:
    """Retrieve dmart settings and configurations.

    Returns:
        Dict containing various dmart settings and configurations.
    """
    return await self._request("GET", f"{self.base_url}/info/settings", headers=self.headers)
