# Pydmart

This is a Python Dmart client (v1.3.x) used to interact with a Dmart instance


## Installation

Pydmart is distributed via [PyPI](https://pypi.org/project/pydmart/):

```bash
pip install pydmart
```

## Example

The `DmartService` class provides methods to interact with a Dmart instance. Below is a detailed explanation of each method available in the class.

* Initialize the service by providing the base URL of the Dmart instance:
```
service = DmartService("http://localhost:8282")
```

* Perform a login action using the provided shortname and password:
```
login = await service.login("dmart", "Test1234")
```

* Fetch the profile of the current user:
```
me = await service.get_profile()
```

* Create a new space:
```
action_request_record = ActionRequestRecord(
    resource_type=ResourceType.space,
    shortname="myspace_test",
    subpath="/",
    attributes={
        "is_active": True
    }
)
action_request = ActionRequest(
    space_name="myspace_test",
    request_type=RequestType.create,
    records=[action_request_record]
)
space = await service.space(action_request)
```

* Remove a space:
```
action_request_record = ActionRequestRecord(
    resource_type=ResourceType.space,
    shortname="myspace_test",
    subpath="/",
    attributes={}
)
action_request = ActionRequest(
    space_name="myspace_test",
    request_type=RequestType.delete,
    records=[action_request_record]
)
space = await service.space(action_request)
```

* Query the spaces:
```
query_request = QueryRequest(
    type=QueryType.spaces,
    space_name="management",
    subpath="/",
    search=""
)
query = await service.query(query_request)
```

## APIs

* `login(shortname: str, password: str) -> ApiResponse`
Performs a login action using the provided shortname and password.

* `login_by(credentials: dict, password: str) -> ApiResponse`
Performs a login action using custom credentials and password.

* `logout() -> ApiResponse`
Performs a logout action.

* `create_user(request: dict) -> ActionResponse`
Creates a new user with the provided request data.

* `update_user(request: dict) -> ActionResponse`
Updates an existing user with the provided request data.

* `check_existing(prop: str, value: str) -> ResponseEntry`
Checks if a user exists based on the provided property and value.

* `get_profile() -> ProfileResponse`
Gets the profile of the current user.

* `query(query: QueryRequest, scope: str = "managed") -> ApiResponse`
Performs a query action with the provided query request and scope.

* `csv(query: QueryRequest) -> ApiResponse`
Queries the entries as a CSV file with the provided query request.

* `space(action: ActionRequest) -> ActionResponse`
Performs actions on spaces with the provided action request.

* `request(action: ActionRequest) -> ActionResponse`
Performs a request action with the provided action request.

* `retrieve_entry(resource_type: ResourceType, space_name: str, subpath: str, shortname: str, retrieve_json_payload: bool = False, retrieve_attachments: bool = False, validate_schema: bool = True, scope: str = "managed") -> ResponseEntry`
Retrieves an entry based on the provided parameters.

* `upload_with_payload(space_name: str, subpath: str, shortname: str, resource_type: ResourceType, payload_file: Any, content_type: Optional[ContentType] = None, schema_shortname: Optional[str] = None) -> ApiResponse`
Uploads a file with payload to the specified space.

* `fetch_data_asset(resource_type: str, data_asset_type: str, space_name: str, subpath: str, shortname: str, query_string: str = "SELECT * FROM file", filter_data_assets: Optional[List[str]] = None, branch_name: Optional[str] = None) -> Dict[str, Any]`
Fetches a data asset based on the provided parameters.

* `get_spaces() -> ApiResponse`
Gets the list of spaces.

* `get_children(space_name: str, subpath: str, limit: int = 20, offset: int = 0, restrict_types: Optional[List[ResourceType]] = None) -> ApiResponse`
Gets the children of a specified space.

* `get_attachment_url(resource_type: ResourceType, space_name: str, subpath: str, parent_shortname: str, shortname: str, ext: Optional[str] = None, scope: str = "managed") -> str`
Gets the URL of an attachment.

* `get_space_health(space_name: str) -> Dict[str, Any]`
Gets the health status of a specified space.

* `get_attachment_content(resource_type: str, space_name: str, subpath: str, shortname: str, scope: str = "managed") -> Dict[str, Any]`
Gets the content of an attachment.

* `get_payload(resource_type: str, space_name: str, subpath: str, shortname: str, ext: str = ".json", scope: str = "managed") -> Dict[str, Any]`
Gets the payload of a specified resource.

* `get_payload_content(resource_type: str, space_name: str, subpath: str, shortname: str, ext: str = ".json", scope: str = "managed") -> Dict[str, Any]`
Gets the content of a payload.

* `progress_ticket(space_name: str, subpath: str, shortname: str, action: str, resolution: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]`
Progresses a ticket with the provided parameters.

* `submit(space_name: str, schema_shortname: str, subpath: str, record: Dict[str, Any]) -> Dict[str, Any]`
Submits a record to the specified space and schema.

* `get_manifest() -> Dict[str, Any]`
Gets the manifest information.

* `get_settings() -> Dict[str, Any]`
Gets the settings information.
