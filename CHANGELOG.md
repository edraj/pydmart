# Changelog

## 2.9.0

**Compatibility:** the second-factor calls need csdmart >= 1.8.1; the rest is
unchanged.

### Added

- **Second factors at sign-in:** `login` takes the second step's `totp` (an
  authenticator app's code), `recovery_code`, or `webauthn` (a security key's
  answer); `login_by` passes them in `credentials`.
  `DmartException.second_factor` reads the step an `OTP_NEEDED` (115) or
  `SECOND_FACTOR_REQUIRED` (116) answer asks for.
- **Key-only sign-in:** `key_only_challenge(**account)` and
  `login_with_key_alone(webauthn, **account)`, for an account that turned it
  on; a tool that talks to the key (python-fido2, say) signs the challenge.
- **The account's second factors:** `get_second_factors`,
  `passkey_proof_challenge`, `new_recovery_codes`, `set_key_only`, and an
  authenticator app's `totp_begin`, `totp_confirm` and `totp_remove`.
- **`DmartErrorCode`** gains `SECOND_FACTOR_REQUIRED` (116) and
  `SECOND_FACTOR_INVALID` (117), as tsdmart and flutterdmart do.

## 2.8.0

**Compatibility:** `login_client_credentials` needs csdmart >= 1.8.0; the rest
is unchanged.

### Added

- **`login_client_credentials(client_id, client_secret, resource=None, token_url=None)`:**
  a service signs in with its own token (OAuth 2 `client_credentials` at
  `/oidc/token`) instead of a bot's password. The token is kept like a
  login's, and a request made when less than min(30 s, half its lifetime)
  remains gets a new one first; concurrent requests share one renewal. A
  refusal raises `DmartException` with the endpoint's OAuth error
  (`invalid_client: ...`). Setting `auth_token`, a password login or
  `logout()` ends the renewal.
- **`ResourceType`** gains `data_asset`, `lock`, `log`, `reply`, `share` and
  `integration`, the types dmart has and the enum lacked.

### Changed

- **`auth_token` is a property.** Reading and writing it works as before;
  writing it ends client-credentials renewal.

## 2.7.0

**Compatibility:** requires csdmart ≥ 1.6.12 (`get_client_config` and
`get_permissions` need it; `get_permissions` falls back on older servers, and
the rest works on older servers too). A top-level `shortname` on sign-up and
the username rule in the client config need ≥ 1.7.9. Aligned with csdmart
1.7.10.

### Added

- **`password_reset_confirm(otp, password, shortname=None, email=None, msisdn=None)`**
  posts `/user/password-reset-confirm`, the second half of the reset flow
  after `otp_request(OtpPurpose.reset, ...)`.
- **`get_client_config()`** reads `GET /public/client-config` without a
  token: OTP length, resend delay and lifetime, upload and query limits, the
  request timeout, and whether custom password and username rules apply, with
  their hints.
- **Device sign-in.** `login(shortname, password, otp=None, device_id=None)`
  covers the two-step sign-in: an admin's password sign-in (dmart 1.6.6+) and
  the first sign-in from a new device (1.7.2+) answer `OTP_NEEDED` (115) and
  send a code, and the client signs in again with the same password, the same
  `device_id` and the `otp`. `password=None` with an `otp` is a code login.
  `DmartService(base_url, device_id=...)` sends `X-DeviceId` on `login` and
  `login_by`; a `device_id` in the body wins. dmart 1.7.2+ refuses a mobile
  sign-in that names no device.
- **`DmartErrorCode`** (IntEnum): the codes clients branch on, with dmart's
  integers: `INVALID_USERNAME_AND_PASS` 10, `USER_ISNT_VERIFIED` 11,
  `SESSION` 50, `PASSWORD_RESET_ERROR` 102, `OTP_RESEND_BLOCKED` 103,
  `USER_ACCOUNT_LOCKED` 110, `OTP_NEEDED` 115, `MISSING_DATA` 202,
  `INVALID_ROUTE` 230, `INVALID_TICKET_STATUS` 300, `OTP_INVALID` 307,
  `OTP_EXPIRED` 308, `SHORTNAME_ALREADY_EXIST` 400, `NOT_ALLOWED` 401,
  `INVALID_DATA` 402, `CONFLICT` 409, `DATA_SHOULD_BE_UNIQUE` 415,
  `PASSWORD_HASHING_BUSY` 503, `REQUEST_TIMEOUT` 504. tsdmart and
  flutterdmart carry the same set under the same name. **`ErrorType`** lists
  the `error.type` values, including the new `server`.
- **`create_user(request, shortname=None)`**: a top-level `shortname` is the
  username the registrant chose, or `"auto"` (dmart 1.7.9+). Since dmart
  1.7.10 open registration always needs `attributes.email_otp` /
  `msisdn_otp`, from `otp_request(OtpPurpose.register, ...)`.
- **`confirm_otp`** takes `password` or `current_code`. Changing an account's
  email or phone (dmart 1.6.7+) needs the password, or, on an account without
  one, a verify-contact code sent to the address it already has.
- **`csv(query, preview=True)`** asks `/managed/csv?preview=1` what the file
  would hold.
- **`ApiResponse.total_is_lower_bound`**: True when the server capped a
  query's count, so `attributes["total"]` is a lower bound.
- `UserType.admin`, `ContentType.binary`. `OtpPurpose`, `DmartErrorCode`
  and `ErrorType` are exported from the package.

### Changed

- **`get_space_health(space_name, health_type="soft")`** calls
  `/managed/health/{health_type}/{space_name}` (`soft`, `hard` or `all`).
  The route is for global admins only since dmart 1.5.19.
- **`QueryRequest.limit` defaults to `None`**, and `query()` / `csv()` leave
  out every unset field. A query that sets no limit gets the server's
  `DEFAULT_QUERY_LIMIT` instead of a hard-coded 10; `-1` asks for
  `MAX_QUERY_LIMIT`.
- **`QueryRequest.validate_schema` is deprecated and never sent.** dmart
  dropped it from queries in 1.5.0.
- Docstrings now cover what dmart 1.6–1.7 expects: `old_password` on every
  password change through `update_user`, `USER_ISNT_VERIFIED` (11) on a
  password sign-in naming an unverified address (1.7.10), and the error
  codes each auth call can answer.
- **`retrieve_entry(validate_schema=...)` is deprecated and no longer sent.**
  dmart's entry route ignores it, so it never validated anything; passing it
  now warns (`DeprecationWarning`).
- **`current_user_permissions` starts as `{}`** and is typed
  `Dict[str, Any]`, matching the permission map `get_permissions()` and
  `get_profile()` store. It used to start as `[]`, so a `.get()` on it before
  the first fetch raised `AttributeError`.

### Fixed

- **`csv()` returns the CSV text.** dmart answers `/managed/csv` with the file
  itself (`text/csv`), but `csv()` read every answer as JSON, so an export
  always raised `DmartException` against a real server. It now returns the
  text (`str`); a refusal still raises with dmart's error. `csv(...,
  preview=True)` returns the JSON preview as before.

### Removed

These called routes csdmart doesn't have, so they always failed against it:

- **`user_reset`** (`/user/reset`, dropped from csdmart in June 2026).
- **`fetch_data_asset`** (`/managed/data-asset`, never ported to csdmart).
- **`space`** (`/managed/space`). Create and delete spaces with `request()`
  and `resource_type=ResourceType.space`.
