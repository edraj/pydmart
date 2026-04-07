"""Shared test helpers for pydmart tests."""

BASE_URL = "http://dmart.test:8282"


def make_success_response(records=None):
    """Helper to build a minimal successful API JSON response."""
    return {
        "status": "success",
        "records": records or [],
    }


def make_failed_response(error_type="request", code=400, message="bad request"):
    """Helper to build a minimal failed API JSON response."""
    return {
        "status": "failed",
        "error": {
            "type": error_type,
            "code": code,
            "message": message,
            "info": [],
        },
    }


def make_login_response(access_token="tok_abc123"):
    """Helper to build a login success response."""
    return make_success_response(records=[{
        "resource_type": "user",
        "shortname": "testuser",
        "subpath": "/",
        "attributes": {"access_token": access_token},
    }])


def make_profile_response(roles=None, permissions=None):
    """Helper to build a profile success response."""
    return make_success_response(records=[{
        "resource_type": "user",
        "shortname": "testuser",
        "subpath": "/",
        "attributes": {
            "roles": roles or ["admin"],
            "permissions": permissions or ["read", "write"],
        },
    }])


def make_entry_response():
    """Helper to build a ResponseEntry-compatible JSON dict."""
    return {
        "uuid": "abc-123",
        "shortname": "myentry",
        "subpath": "/content",
        "is_active": True,
        "tags": ["tag1", "tag2"],
    }
