# Architecture Summary

Single-file Python service (`app.py`, 187 LOC) using **only the standard library** —
no web framework, no third-party dependencies. SQLite is the persistence layer.

## Modules / components

- **`connect(database)`** — opens a SQLite connection with `Row` factory and creates the
  `books` table (`id`, `title`, `author`, `year`, `isbn`) if absent. Idempotent schema setup.
- **`book_dict(row)`** — serialises a SQLite row into the public JSON shape.
- **`BookAPI`** — a WSGI-style callable (`__call__(environ, start_response)`) whose
  `dispatch(method, path, query, data)` is the single routing core. This is the unit under
  test (`test_app.py` drives it through a synthetic WSGI environ). Handles `/health`,
  `/books` (list + `?author=` filter + create), and `/books/{id}` (get/put/delete).
- **`BookHandler`** — a `BaseHTTPRequestHandler` subclass providing the real HTTP server
  front end (`do_GET/do_POST/do_PUT/do_DELETE` → `dispatch_http`), plus the shared static
  helpers `book_id(path)` (path parsing → int id) and `validate(data)` (field validation).
  It delegates routing to `BookAPI.dispatch`.
- **`serve(host, port, database)`** — wires a `BookAPI` into `BookHandler` and runs a
  `ThreadingHTTPServer`. Configurable via `HOST`, `PORT`, `BOOKS_DATABASE` env vars.

## Request flow

`ThreadingHTTPServer` → `BookHandler.do_*` → `dispatch_http` → `BookAPI.dispatch` →
per-method SQLite query via `connect()` → `(status, payload)` → JSON-encoded response.
The test suite bypasses the HTTP layer and calls `BookAPI` directly as a WSGI app.

## Notes

- Validation lives in `BookHandler.validate` (static) and is reused by both the WSGI create/
  update paths and the HTTP handler — one source of truth for "title and author required".
- Two entry surfaces share one dispatch core; the WSGI surface (`BookAPI.__call__`) exists
  largely to make routing testable without binding a socket. The `BaseHTTPRequestHandler`
  surface (`do_*`, `send_json`, `read_body`) is exercised only in production, not by tests.
