# Architecture summary — rest-api-crud (python, claude-fable-5-2, effort=low)

Single-file service in `app.py` (238 LoC), stdlib-only (`http.server` + `sqlite3`),
no third-party runtime dependencies. `pytest` is the only dev dependency.

## Modules / components

| Component | Location | Responsibility |
|---|---|---|
| `validate_book` | app.py:25-51 | Validates/normalises a payload; raises `ValidationError` with per-field details. Rejects bool-as-int for `year`, non-string `isbn`. |
| `BookStore` | app.py:54-111 | SQLite persistence. One connection guarded by a `threading.Lock`; `create/list/get/update/delete`. Table auto-created in `__init__`. |
| `BookHandler` | app.py:121-208 | `BaseHTTPRequestHandler` subclass. `_route` dispatches method+path; `_send` serialises JSON + Content-Length; `_dispatch` maps exceptions to status codes. |
| `create_server` / `main` | app.py:211-234 | `ThreadingHTTPServer` factory + CLI (`--host/--port/--db`). |

## Request flow

`do_GET/POST/PUT/DELETE/PATCH` → `_dispatch` → `_route`:
- `/health` (GET) → 200 `{"status":"ok"}`
- `/books` GET (optional `?author=`, case-insensitive exact match) / POST (validate → 201)
- `/books/{id}` (regex `^/books/(\d+)$`) GET / PUT (validate → 200) / DELETE (204)
- unmatched path → 404; wrong method on known path → 405

Exceptions: `ValidationError`→400 with `details`, `HTTPError`→its status, bare `Exception`→500.

## Tests

`test_app.py` (13 functions; one parametrised with 7 cases) drives the **real** HTTP
server on an ephemeral port against a temp SQLite file — genuine integration tests,
not mocks. Covers health, CRUD round-trips, author filter, validation matrix,
invalid/non-object JSON bodies, 404/405, and on-disk SQLite persistence across reopen.
