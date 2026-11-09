from enum import IntEnum, StrEnum


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
    admin = "admin"


class OtpPurpose(StrEnum):
    login = "login"
    reset = "reset"
    register = "register"
    verify_contact = "verify-contact"


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


class JoinType(StrEnum):
    left = "left"
    right = "right"
    inner = "inner"
    outer = "outer"


class SortType(StrEnum):
    ascending = "ascending"
    descending = "descending"


class RequestType(StrEnum):
    create = "create"
    update = "update"
    progress_ticket = "progress_ticket"
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
    binary = "binary"


class ContentTypeMedia(StrEnum):
    text = "text"
    html = "html"
    markdown = "markdown"
    image = "image"
    python = "python"
    pdf = "pdf"
    audio = "audio"
    video = "video"


class DmartErrorCode(IntEnum):
    """dmart's ``error.code`` values a client is most likely to branch on.

    Read them off ``DmartException.error.code``. The numbers match csdmart's
    ``Dmart.Models/Api/InternalErrorCode.cs``; tsdmart and flutterdmart carry
    the same set under the same name.
    """
    # Sign-in and accounts
    INVALID_USERNAME_AND_PASS = 10
    """Wrong shortname, email, msisdn or password."""
    USER_ISNT_VERIFIED = 11
    """Password sign-in named an email or phone that isn't verified yet.
    Offer a code login (``otp_request(OtpPurpose.login, ...)``) or a reset."""
    SESSION = 50
    """The token or session isn't valid. ``/user/create`` also answers this
    for a refused registration."""
    PASSWORD_RESET_ERROR = 102
    USER_ACCOUNT_LOCKED = 110
    OTP_NEEDED = 115
    """Sign-in needs a second step: a code was sent; call ``login`` again with
    the same identifier, password, ``device_id`` and the ``otp``."""
    NOT_ALLOWED = 401
    # Codes
    OTP_RESEND_BLOCKED = 103
    """A new code was asked for too soon."""
    OTP_INVALID = 307
    OTP_EXPIRED = 308
    # Data
    MISSING_DATA = 202
    INVALID_ROUTE = 230
    INVALID_TICKET_STATUS = 300
    SHORTNAME_ALREADY_EXIST = 400
    INVALID_DATA = 402
    CONFLICT = 409
    """The record changed after the write was authorized; re-read and retry."""
    DATA_SHOULD_BE_UNIQUE = 415
    """An email or msisdn is already used by another account."""
    # Server
    PASSWORD_HASHING_BUSY = 503
    REQUEST_TIMEOUT = 504


class ErrorType(StrEnum):
    """dmart's ``error.type`` values (csdmart ``Dmart.Models/Api/ErrorTypes.cs``)."""
    auth = "auth"
    jwtauth = "jwtauth"
    db = "db"
    request = "request"
    create = "create"
    exception = "exception"
    server = "server"
    """The server couldn't finish within its own limits (timeout, hashing budget)."""
    restriction = "restriction"
    internal = "internal"
    media = "media"
    attachment = "attachment"
    qr = "qr"
    channel_auth = "channel_auth"
