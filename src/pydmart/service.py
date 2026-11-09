import json
import warnings
import aiohttp
from typing import Any, Dict, List, Literal, Optional, Union, overload
from .models import (
    ApiResponse, ResponseEntry, QueryRequest, ActionRequest,
    DmartException, Error
)
from .enums import QueryType, ResourceType, ContentType, OtpPurpose, DmartErrorCode


# dmart's error code for a route the server does not have.
INVALID_ROUTE = int(DmartErrorCode.INVALID_ROUTE)


class DmartService:
    """High-level async client for the Dmart HTTP API.

    This service wraps the Dmart backend endpoints with convenient coroutine
    methods. Create a single instance per base_url and reuse it to keep the
    authentication token. Most methods return pydantic models that mirror the
    API responses.

    Supports async context manager protocol for automatic session lifecycle::

        async with DmartService("https://api.example.com") as service:
            await service.login("user", "pass")
            data = await service.get_spaces()

    Attributes:
        base_url: Base endpoint of the Dmart service, e.g. https://api.example.com
        auth_token: Bearer token assigned upon successful login.
        current_user_roles: Cached roles from the user profile, if fetched.
        current_user_permissions: Cached permission map, from get_permissions()
            or the user profile, if fetched.
        device_id: Optional device identifier sent as the ``X-DeviceId`` header
            on sign-in. dmart (>= 1.7.2) requires a device id for mobile
            accounts; a ``device_id`` passed to ``login`` wins over it.
    """

    def __init__(self, base_url: str, device_id: Optional[str] = None):
        """Initialize the service.

        Args:
            base_url: Base URL of the Dmart API (without trailing slash).
            device_id: Optional device identifier for sign-in (``X-DeviceId``).
        """
        self.base_url: str = base_url
        self.device_id: Optional[str] = device_id
        self.auth_token: str = ""
        self.current_user_roles: List[str] = []
        self.current_user_permissions: Dict[str, Any] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "DmartService":
        """Enter the async context manager; creates a reusable HTTP session."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager; closes the HTTP session."""
        await self.close()

    async def connect(self) -> None:
        """Create the underlying aiohttp session for connection pooling.

        Call this once before making requests, or use the async context
        manager instead. Safe to call multiple times.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close the underlying aiohttp session.

        Always call this when done, or use the async context manager.
        """
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return the current session, creating one lazily if needed."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

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

    async def _request(self, method: str, url: str, **kwargs: Any) -> ApiResponse:
        """Low-level request wrapper that normalizes responses and errors.

        Args:
            method: HTTP method (e.g., 'GET', 'POST').
            url: Fully qualified request URL.
            **kwargs: Passed through to aiohttp.ClientSession.request.

        Returns:
            ApiResponse parsed from the server response.

        Raises:
            DmartException: On HTTP errors or when the server returns a
                failure status.
        """
        try:
            session = await self._get_session()
            async with session.request(method, url, **kwargs) as response:
                data = await response.json()
                try:
                    if data['status'] == 'failed':
                        raise DmartException(status_code=400, error=Error(**data['error']))
                    return ApiResponse(**data)
                except DmartException:
                    raise
                except Exception as e:
                    err = data.get('error', {
                        'type': 'request',
                        'code': 500,
                        'message': str(e)
                    })
                    error = Error(**err)
                    raise DmartException(status_code=400, error=error)
        except DmartException:
            raise
        except aiohttp.ClientResponseError as e:
            raise DmartException(status_code=e.status, error=Error(type="ClientResponseError", code=e.status, message=e.message, info=[]))
        except aiohttp.ClientError as e:
            raise DmartException(status_code=500, error=Error(type="ClientError", code=500, message=str(e), info=[]))

    @property
    def _login_headers(self) -> Dict[str, str]:
        """JSON headers for /user/login, with ``X-DeviceId`` when a client device id is set."""
        headers = {"Content-Type": "application/json"}
        if self.device_id:
            headers["X-DeviceId"] = self.device_id
        return headers

    async def login(
        self,
        shortname: str,
        password: Optional[str],
        otp: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> ApiResponse:
        """Login with shortname and password (and/or code); stores auth token on success.

        Sign-in can take two steps. When dmart answers ``OTP_NEEDED`` (115) it
        has sent a code: an admin always, and (dmart >= 1.7.2) any account
        signing in from a device it hasn't seen. Call ``login`` again with the
        same shortname, password and ``device_id`` plus the ``otp``. A code
        login (from ``otp_request(OtpPurpose.login, ...)``) passes
        ``password=None`` and the ``otp``.

        Mobile accounts must send a device id (here, or ``device_id`` on the
        service, which goes out as ``X-DeviceId``); without one dmart answers
        ``INVALID_DATA`` (402) or 115.

        Args:
            shortname: User shortname.
            password: User password, or None for a code login.
            otp: Code from the second step or a code login.
            device_id: Device identifier; overrides the service's ``device_id``.

        Returns:
            ApiResponse containing the login record with access_token.

        Raises:
            DmartException: On failure. Check ``error.code`` against
                ``DmartErrorCode``: ``OTP_NEEDED`` (115) means send the
                code, ``USER_ISNT_VERIFIED`` (11) means that address isn't
                verified (offer a code login or reset), ``USER_ACCOUNT_LOCKED``
                (110) a lockout or a device-locked account.
        """
        body: Dict[str, Any] = {"shortname": shortname}
        if password is not None:
            body["password"] = password
        if otp is not None:
            body["otp"] = otp
        if device_id is not None:
            body["device_id"] = device_id
        data = await self._request(
            "POST",
            f"{self.base_url}/user/login",
            json=body,
            headers=self._login_headers,
        )
        if not data.records or len(data.records) == 0:
            raise DmartException(
                status_code=500,
                error=Error(type="ClientError", code=500, message="Invalid response: no records", info=[])
            )
        record = data.records[0]
        if record.attributes:
            self.auth_token = record.attributes.get("access_token", "")
        return data

    async def login_by(self, credentials: Dict[str, Any], password: str) -> ApiResponse:
        """Login with arbitrary credentials dict plus password; stores auth token.

        ``credentials`` may also carry ``otp`` and ``device_id`` for the
        two-step sign-in described on ``login``. The service's ``device_id``
        goes out as ``X-DeviceId``; a ``device_id`` in ``credentials`` wins.

        Args:
            credentials: Dict with authentication fields (e.g. email, msisdn,
                otp, device_id).
            password: User password.

        Returns:
            ApiResponse containing the login record with access_token.

        Raises:
            DmartException: On invalid credentials or malformed response.
        """
        data = await self._request(
            "POST",
            f"{self.base_url}/user/login",
            json={**credentials, "password": password},
            headers=self._login_headers,
        )
        if data.records:
            self.auth_token = data.records[0].attributes.get("access_token", "")
        return data

    async def logout(self) -> ApiResponse:
        """Invalidate current token server-side (if any)."""
        return await self._request("POST", f"{self.base_url}/user/logout", headers=self.headers)

    async def create_user(self, request: Dict[str, Any], shortname: Optional[str] = None) -> ApiResponse:
        """Register a new user (POST /user/create).

        The body is ``{"shortname"?: ..., "attributes": {...}}``. Attributes
        carry ``email`` and/or ``msisdn``, ``password``, ``displayname`` and so
        on, plus ``email_otp`` / ``msisdn_otp``: codes from
        ``otp_request(OtpPurpose.register, ...)``. Open registration always
        needs those codes on dmart >= 1.7.10. dmart answers ``OTP_INVALID``
        (307) or ``OTP_EXPIRED`` (308) for a bad code.

        Args:
            request: The request body, usually ``{"attributes": {...}}``.
            shortname: Optional username to register under (dmart >= 1.7.9):
                a free name that passes the server's username rule, or
                ``"auto"`` to let the server pick one. Overrides a
                ``shortname`` already in ``request``.
        """
        body = dict(request)
        if shortname is not None:
            body["shortname"] = shortname
        return await self._request("POST", f"{self.base_url}/user/create", json=body, headers=self.json_headers)

    async def update_user(self, request: Dict[str, Any]) -> ApiResponse:
        """Update current user profile attributes.

        Note: this endpoint no longer accepts contact-change fields (email,
        new_email, email_otp, msisdn, new_msisdn, msisdn_otp) and will error
        if they are present. Use otp_request(purpose=OtpPurpose.verify_contact)
        followed by confirm_otp() to confirm a new email or msisdn.

        Changing the password needs ``old_password`` alongside ``password``,
        even under ``force_password_change`` (dmart >= 1.6.6). An account with
        no password sets its first one through the reset flow
        (``password_reset_confirm``).

        Args:
            request: Payload for the update endpoint.
        """
        return await self._request("POST", f"{self.base_url}/user/profile", json=request, headers=self.json_headers)

    async def check_existing(self, prop: str, value: str) -> ApiResponse:
        """Check whether a user property already exists (e.g., email or shortname)."""
        return await self._request("GET", f"{self.base_url}/user/check-existing?{prop}={value}", headers=self.headers)

    async def get_profile(self) -> ApiResponse:
        """Fetch current user profile and cache permissions/roles on success.

        dmart deprecates the profile's permission map in favour of
        GET /user/permissions (get_permissions()). Once a server leaves it
        out, the cached map is kept rather than cleared.
        """
        data = await self._request("GET", f"{self.base_url}/user/profile", headers=self.headers)
        if data.status == "success" and data.records:
            attributes = data.records[0].attributes
            if "permissions" in attributes:
                self.current_user_permissions = attributes["permissions"] or {}
            self.current_user_roles = attributes.get("roles", [])
        return data

    async def get_permissions(self) -> Dict[str, Any]:
        """Fetch the caller's permission map and cache it.

        Reads GET /user/permissions, keyed "space:subpath:resource_type".
        A server without that route answers INVALID_ROUTE (230, with HTTP
        422) and is answered from the profile, which carried the map until
        then.

        Raises:
            DmartException: On any other failure.
        """
        try:
            data = await self._request("GET", f"{self.base_url}/user/permissions", headers=self.headers)
            permissions = (getattr(data, "attributes", None) or {}).get("permissions")
        except DmartException as e:
            if e.error.code != INVALID_ROUTE and e.status_code != 404:
                raise
            profile = await self.get_profile()
            permissions = profile.records[0].attributes.get("permissions") if profile.records else None
        result: Dict[str, Any] = permissions or {}
        self.current_user_permissions = result
        return result

    @staticmethod
    def _query_body(query: QueryRequest) -> Dict[str, Any]:
        """Serialize a query, leaving out unset fields and the removed ``validate_schema``.

        Omitting ``limit`` lets the server apply its ``DEFAULT_QUERY_LIMIT``.
        """
        return query.model_dump(mode="json", exclude_none=True, exclude={"validate_schema"})

    async def query(self, query: QueryRequest, scope: str = "managed") -> ApiResponse:
        """Run a query within a scope.

        ``data.attributes`` carries ``total`` and ``returned``; when the server
        capped the count, ``data.total_is_lower_bound`` is True.

        Args:
            query: QueryRequest payload.
            scope: API scope, e.g. 'managed' or 'public'.
        """
        return await self._request("POST", f"{self.base_url}/{scope}/query", json=self._query_body(query), headers=self.json_headers)

    @overload
    async def csv(self, query: QueryRequest, preview: Literal[False] = False) -> str: ...

    @overload
    async def csv(self, query: QueryRequest, preview: Literal[True]) -> ApiResponse: ...

    async def csv(self, query: QueryRequest, preview: bool = False) -> Union[str, ApiResponse]:
        """Export a query as CSV (server-side generation).

        dmart answers the file itself (``text/csv``), so this returns the CSV
        text. A refusal still arrives as dmart's JSON error and raises
        ``DmartException``.

        Args:
            query: The query to export.
            preview: Ask for a preview instead (``?preview=1``, dmart >= 1.6.12).
                The answer is then a JSON ``ApiResponse`` whose ``attributes``
                carries ``exported``, ``total``, ``limit``, ``truncated``,
                ``reason`` and ``message``.

        Returns:
            The CSV text, or with ``preview=True`` the preview ``ApiResponse``.
        """
        url = f"{self.base_url}/managed/csv"
        body = self._query_body(query)
        if preview:
            return await self._request("POST", f"{url}?preview=1", json=body, headers=self.json_headers)
        try:
            session = await self._get_session()
            async with session.post(url, json=body, headers=self.json_headers) as response:
                failed = response.status >= 400
                if failed or "json" in (response.content_type or ""):
                    try:
                        data = await response.json(content_type=None)
                    except ValueError:
                        data = None
                    if isinstance(data, dict) and data.get("status") == "failed" and isinstance(data.get("error"), dict):
                        raise DmartException(status_code=response.status if failed else 400, error=Error(**data["error"]))
                    if failed:
                        raise DmartException(
                            status_code=response.status,
                            error=Error(type="request", code=response.status, message=(await response.text())[:500], info=[]),
                        )
                return await response.text()
        except DmartException:
            raise
        except aiohttp.ClientError as e:
            raise DmartException(status_code=500, error=Error(type="ClientError", code=500, message=str(e), info=[]))

    async def request(self, action: ActionRequest) -> ApiResponse:
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
        validate_schema: Optional[bool] = None,
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
            validate_schema: Deprecated and never sent: dmart's entry route
                ignores it, so it never validated anything.
            scope: API scope.

        Returns:
            ResponseEntry with the full resource data.
        """
        url = (
            f"{self.base_url}/{scope}/entry/{resource_type}/{space_name}"
            f"/{subpath}/{shortname}"
            f"?retrieve_json_payload={retrieve_json_payload}"
            f"&retrieve_attachments={retrieve_attachments}"
        )
        if validate_schema is not None:
            warnings.warn(
                "retrieve_entry(validate_schema=...) is deprecated: dmart ignores it and it is no longer sent.",
                DeprecationWarning,
                stacklevel=2,
            )
        try:
            session = await self._get_session()
            async with session.request("GET", url, headers=self.headers) as response:
                data = await response.json()
                if data.get('status') == 'failed':
                    raise DmartException(status_code=400, error=Error(**data['error']))
                return ResponseEntry(**data)
        except DmartException:
            raise
        except aiohttp.ClientResponseError as e:
            raise DmartException(status_code=e.status, error=Error(type="ClientResponseError", code=e.status, message=e.message, info=[]))
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
        request_record_body: Dict[str, Any] = {
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

    async def get_space_health(self, space_name: str, health_type: str = "soft") -> ApiResponse:
        """Get health information for a space.

        Global admins only (dmart >= 1.5.19); others get a refusal.

        Args:
            space_name: Space to check.
            health_type: ``"soft"``, ``"hard"`` or ``"all"``.
        """
        return await self._request("GET", f"{self.base_url}/managed/health/{health_type}/{space_name}", headers=self.headers)

    async def get_payload(
        self,
        resource_type: str,
        space_name: str,
        subpath: str,
        shortname: str,
        schema_shortname: str = "",
        ext: str = ".json",
        scope: str = "managed"
    ) -> ApiResponse:
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
        return await self._request(
            "GET",
            f"{self.base_url}/{scope}/payload/{resource_type}/{space_name}/{subpath}/{shortname}{schema_shortname}{ext}",
            headers=self.headers,
        )

    async def progress_ticket(
        self,
        space_name: str,
        subpath: str,
        shortname: str,
        action: str,
        resolution: Optional[str] = None,
        comment: Optional[str] = None
    ) -> ApiResponse:
        """Move a ticket through its workflow with optional resolution/comment."""
        payload: Dict[str, str] = {}
        if resolution:
            payload["resolution"] = resolution
        if comment:
            payload["comment"] = comment

        return await self._request(
            "PUT",
            f"{self.base_url}/managed/progress-ticket/{space_name}/{subpath}/{shortname}/{action}",
            json=payload,
            headers=self.json_headers,
        )

    async def submit(
        self,
        space_name: str,
        schema_shortname: str,
        subpath: str,
        record: Dict[str, Any],
        resource_type: Optional[ResourceType] = None,
        workflow_shortname: Optional[str] = None
    ) -> ApiResponse:
        """Public submit of a record to a space/schema, optionally via workflow."""
        url = f"{self.base_url}/public/submit/{space_name}"
        if resource_type:
            url += f"/{resource_type.value}"
        if workflow_shortname:
            url += f"/{workflow_shortname}"
        url += f"/{schema_shortname}/{subpath}"

        return await self._request("POST", url, json=record, headers=self.json_headers)

    async def otp_request(self, purpose: OtpPurpose, msisdn: Optional[str] = None, email: Optional[str] = None, shortname: Optional[str] = None, accept_language: Optional[str] = None) -> ApiResponse:
        """Request an OTP via msisdn, email, or shortname for the given purpose.

        Args:
            purpose: Why the OTP is requested (login, reset, register, or
                verify_contact). Required by the server.
            msisdn: Destination phone number, if using msisdn.
            email: Destination email, if using email.
            shortname: Target user's shortname, if using shortname (e.g. reset).
            accept_language: Optional Accept-Language header override.
        """
        payload: Dict[str, str] = {"purpose": purpose}
        if msisdn:
            payload["msisdn"] = msisdn
        if email:
            payload["email"] = email
        if shortname:
            payload["shortname"] = shortname

        headers = {**self.json_headers}
        if accept_language:
            headers["Accept-Language"] = accept_language

        return await self._request("POST", f"{self.base_url}/user/otp-request", json=payload, headers=headers)

    async def confirm_otp(
        self,
        otp: str,
        msisdn: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        current_code: Optional[str] = None,
    ) -> ApiResponse:
        """Verify a contact's OTP code sent to msisdn or email (POST /user/verify-contact).

        Call otp_request(purpose=OtpPurpose.verify_contact, ...) first to
        trigger the code, then pass it here to confirm.

        Confirming the address already on the account needs nothing else.
        Changing it (dmart >= 1.6.7) needs ``password`` on an account that has
        one (admins always), or ``current_code`` on a passwordless account: a
        verify-contact code sent to its existing phone, else its email.

        Args:
            otp: The code sent to the new address.
            msisdn: The phone being confirmed.
            email: The email being confirmed.
            password: The account's password, to change an address.
            current_code: A code sent to the existing address, for a
                passwordless account changing its address.
        """
        payload: Dict[str, str] = {"code": otp}
        if msisdn:
            payload["msisdn"] = msisdn
        if email:
            payload["email"] = email
        if password is not None:
            payload["password"] = password
        if current_code is not None:
            payload["current_code"] = current_code

        return await self._request("POST", f"{self.base_url}/user/verify-contact", json=payload, headers=self.json_headers)

    async def password_reset_confirm(
        self,
        otp: str,
        password: str,
        shortname: Optional[str] = None,
        email: Optional[str] = None,
        msisdn: Optional[str] = None,
    ) -> ApiResponse:
        """Set a new password with a reset code (POST /user/password-reset-confirm).

        Get the code with ``otp_request(OtpPurpose.reset, ...)`` and name the
        account with exactly one of ``shortname``, ``email`` or ``msisdn``
        (a server may refuse ``shortname``; then use email or msisdn). An
        admin can reset only while ``force_password_change`` is set.

        Args:
            otp: The reset code.
            password: The new password.
            shortname: The account's shortname.
            email: The account's email.
            msisdn: The account's phone.

        Raises:
            DmartException: ``OTP_INVALID`` (307), ``OTP_EXPIRED`` (308),
                ``MISSING_DATA`` (202) or ``PASSWORD_RESET_ERROR`` (102).
        """
        body: Dict[str, str] = {"otp": otp, "password": password}
        if shortname:
            body["shortname"] = shortname
        if email:
            body["email"] = email
        if msisdn:
            body["msisdn"] = msisdn
        return await self._request("POST", f"{self.base_url}/user/password-reset-confirm", json=body, headers=self.json_headers)

    async def validate_password(self, password: str) -> ApiResponse:
        """Validate password strength/policy server-side."""
        return await self._request("POST", f"{self.base_url}/user/validate_password", json={"password": password}, headers=self.json_headers)

    async def get_manifest(self) -> ApiResponse:
        """Retrieve server manifest information.

        Returns:
            ApiResponse containing version, build info and other manifest details.
        """
        return await self._request("GET", f"{self.base_url}/info/manifest", headers=self.headers)

    async def get_client_config(self) -> ApiResponse:
        """Read the server's client configuration (GET /public/client-config, dmart >= 1.6.12).

        Needs no sign-in. ``data.attributes`` carries ``backend_timeout``,
        ``otp_length``, ``otp_resend_after``, ``otp_token_ttl``,
        ``max_upload_size_mb``, ``default_query_limit``, ``max_query_limit``,
        ``ui_list_limit``, ``password_rule_custom``, ``password_hint`` (when
        set), and on dmart >= 1.7.9 ``username_rule_custom`` and
        ``username_hint`` (when set).
        """
        return await self._request("GET", f"{self.base_url}/public/client-config")

    async def get_settings(self) -> ApiResponse:
        """Retrieve dmart settings and configurations.

        Returns:
            ApiResponse containing various dmart settings and configurations.
        """
        return await self._request("GET", f"{self.base_url}/info/settings", headers=self.headers)
