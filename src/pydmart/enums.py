from enum import StrEnum


class Status(StrEnum):
    success = "success"
    failed = "failed"


class Language(StrEnum):
    arabic = "arabic"
    english = "english"
    kurdish = "kurdish"
    french = "french"
    turkish = "turkish"


class UserType(StrEnum):
    web = "web"
    mobile = "mobile"
    bot = "bot"


class QueryType(StrEnum):
    aggregation = "aggregation"
    search = "search"
    subpath = "subpath"
    events = "events"
    history = "history"
    tags = "tags"
    spaces = "spaces"
    counters = "counters"
    reports = "reports"
    attachments = "attachments"
    attachments_aggregation = "attachments_aggregation"


class SortType(StrEnum):
    ascending = "ascending"
    descending = "descending"


class RequestType(StrEnum):
    create = "create"
    update = "update"
    replace = "replace"
    delete = "delete"
    move = "move"
    update_acl = "update_acl"
    assign = "assign"


class ResourceAttachmentType(StrEnum):
    json = "json"
    comment = "comment"
    media = "media"
    relationship = "relationship"
    alteration = "alteration"
    csv = "csv"
    parquet = "parquet"
    jsonl = "jsonl"
    sqlite = "sqlite"


class ResourceType(StrEnum):
    user = "user"
    group = "group"
    folder = "folder"
    schema = "schema"
    content = "content"
    acl = "acl"
    comment = "comment"
    reaction = "reaction"
    media = "media"
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
    post = "post"
    plugin_wrapper = "plugin_wrapper"
    notification = "notification"
    jsonl = "jsonl"
    csv = "csv"
    sqlite = "sqlite"
    parquet = "parquet"


class ContentType(StrEnum):
    text = "text"
    html = "html"
    markdown = "markdown"
    json = "json"
    image = "image"
    python = "python"
    pdf = "pdf"
    audio = "audio"
    video = "video"
    jsonl = "jsonl"
    csv = "csv"
    sqlite = "sqlite"
    parquet = "parquet"


class ContentTypeMedia(StrEnum):
    text = "text"
    html = "html"
    markdown = "markdown"
    image = "image"
    python = "python"
    pdf = "pdf"
    audio = "audio"
    video = "video"
