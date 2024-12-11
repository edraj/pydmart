
from enum import StrEnum


class Status(StrEnum):
    success = "success"
    failed = "failed"
    
    
class RequestType(StrEnum):
    create = "create"
    update = "update"
    patch = "patch"
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
    


