# Run Summary: rest-api-crud (python · opus-5-5 · effort=medium · rep2)

## Surface

A book-collection REST API: create/list/get/update/delete books plus a health
check, JSON in/out with correct status codes, SQLite persistence, and input
validation. See `TASK.md`.

## Architecture

Single-module design (`app.py`) on the Python **standard library only** — no web
framework, no ORM. Three concerns, cleanly separated:

1. **`validate_book`** — pure validation → cleaned dict or `ApiError(400)`.
2. **`BookStore`** — SQLite persistence, one connection per operation (so the
   `ThreadingHTTPServer` is safe); parameterized SQL throughout.
3. **`BookHandler`** — `BaseHTTPRequestHandler` subclass; `_dispatch` → `_route`
   maps `(method, path)` to a handler, funneling `ApiError` and unexpected
   exceptions into JSON responses (no traceback leaks).

Control flow: `do_*` → `_dispatch` (exception boundary) → `_route` (path match +
method guard via `_require`) → `BookStore` → `_send`.

See `modules.md` and `interfaces.md` for detail.

## Notable qualities

- Defensive HTTP handling: `Content-Length` parsing, 413 on oversized bodies,
  405 with `Allow` header, malformed/empty/non-object JSON rejected.
- SQL-injection-safe author filter (parameterized + `COLLATE NOCASE`), covered
  by a dedicated test.
- `PUT` documented and tested as a full replace (omitted fields reset to null).
- Configurable via `HOST`/`PORT`/`BOOKS_DB` env vars.
