# Architecture Summary — rest-api-crud (python, claude-fable-5-1)

Single-module service (`app.py`, 269 lines) built entirely on the Python
standard library — `http.server.ThreadingHTTPServer` + `sqlite3`, no third-party
runtime dependencies.

## Modules / components

- **`validate_book(data)`** — pure input validation. Requires non-empty string
  `title`/`author`; optional `year` (int) and `isbn` (str). Raises
  `ValidationError(errors)` with a per-field error list.
- **`BookStore`** — SQLite persistence layer. One shared `sqlite3` connection
  (`check_same_thread=False`) guarded by a `threading.Lock`; CRUD methods
  `create/list/get/update/delete`. Table auto-created on init. `list(author=)`
  filters case-insensitively (`COLLATE NOCASE`), ordered by id.
- **`BookHandler(BaseHTTPRequestHandler)`** — routing + HTTP concerns.
  `_route(method)` dispatches on path (`/health`, `/books`, `/books/{id}` via
  regex). Helpers: `_send_json`, `_error`, `_read_json` (bounded 1 MB body,
  handles bad Content-Length / malformed JSON), `_read_book`,
  `_method_not_allowed` (sends `Allow` header).
- **`create_server` / `main`** — builds a handler subclass bound to its own
  `BookStore`; CLI flags `--host/--port/--db`.

## Request flow

`do_GET/POST/PUT/DELETE/PATCH` → `_route` → path match → (for writes)
`_read_book` → `BookStore` → `_send_json`. Status codes: 200/201/204 success,
400 validation/bad-JSON, 404 missing book/route, 405 method, 413 oversized body.

## Tests

`test_app.py` (159 lines) spins up the real server on an ephemeral port with a
temp SQLite db per test. 12 test functions, one parametrized ×8 → 19 collected
items, 0 skips. Covers health, CRUD round-trips, author filter, validation
rejection matrix, malformed JSON, 404/405 routing, and cross-restart
persistence.
