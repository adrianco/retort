# Architecture Summary

Single-file stdlib-only Python HTTP service (`app.py`, 301 LOC) plus an
integration test module (`test_app.py`, 229 LOC). No third-party runtime deps;
`pytest` is the only dev dependency.

## Modules / components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `BookStore` | `app.py:26-99` | SQLite persistence (thread-safe via a shared connection + lock); CRUD + `ping`. Works with `:memory:` or a file DB. |
| `validate_book` | `app.py:102-140` | Payload validation/normalisation; returns `(book, errors)`. Enforces required `title`/`author`, type/range checks on `year`, string `isbn`. |
| `HTTPError` | `app.py:143-148` | Structured error → HTTP status + JSON body. |
| `BookHandler` | `app.py:151-267` | Request router (`_route`) over `BaseHTTPRequestHandler`; method allow-lists, body-size cap, JSON I/O helpers. |
| `make_server` / `main` | `app.py:270-297` | `ThreadingHTTPServer` wiring; CLI/env config for host/port/db. |

## Request flow

`do_*` → `_dispatch` (catches `HTTPError` → JSON error, else 500) → `_route`
matches `/health`, `/books`, or `/books/{id}` (regex, id capped at 18 digits) →
delegates to `BookStore` → `_send_json` / `_send_empty`.

## Notable engineering choices

- Whole-resource `PUT` semantics (omitted fields cleared) — documented in tests.
- Case-insensitive, whole-name `?author=` filter (`COLLATE NOCASE`).
- 1 MiB request-body cap rejected on `Content-Length` before reading (413).
- `Location` header returned on 201 create.
- Tests drive a real server on an ephemeral port over HTTP (true integration).
