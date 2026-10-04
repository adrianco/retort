# Architecture Summary

Single-module Python service using **only the standard library** (`http.server` +
`sqlite3`) — no runtime dependencies.

## Modules

- **`app.py`** (217 lines) — the whole service:
  - `BookStore` (app.py:21) — SQLite-backed persistence; thread-safe via a
    `threading.Lock`, one shared connection (`check_same_thread=False`). CRUD:
    `create`/`list`/`get`/`update`/`delete`. Schema created on init with
    `title`/`author NOT NULL`, nullable `year`/`isbn`.
  - `validate_book` (app.py:85) — payload validation; `title`+`author` required
    non-empty strings, `year` optional int (rejects bool), `isbn` optional str.
    Raises `ValidationError` → 400.
  - `BookHandler` (app.py:110) — `BaseHTTPRequestHandler`, HTTP/1.1. `_route`
    dispatches by path/method; `_send`/`_error` marshal JSON + status codes.
    Routes: `/health`, `/books` (GET list+`?author=`, POST), `/books/{id}`
    (GET/PUT/DELETE).
  - `make_server` / `main` (app.py:195, 201) — `ThreadingHTTPServer`; host/port/db
    configurable via env vars.
- **`test_app.py`** (119 lines) — pytest integration suite; spins a real server on
  an ephemeral port against a temp-file DB and drives it over HTTP with `urllib`.

## Request flow

`do_<METHOD>` → `_route(method)` → path match → (`validate_book` for write bodies)
→ `BookStore` op → `_send(status, payload)`. All exceptions funnel to `_error`
(400 validation, 404 not-found, 405 method-not-allowed, 500 catch-all).

## Notes

- PUT is a full replacement (documented in README) — requires `title`+`author`.
- `?author=` filter is exact, case-insensitive (`COLLATE NOCASE`).
- Bounded request body (`MAX_BODY = 1_000_000`).
