# Architecture Summary

Single-file stdlib service — no third-party runtime dependencies.

## Modules

- **`app.py`** (289 lines) — the whole service:
  - `BookStore` — SQLite-backed repository (`sqlite3`, `check_same_thread=False`
    guarded by a `threading.Lock`). CRUD + `ping()` for health. Default file DB
    `books.db`; `:memory:` supported.
  - `validate_book(payload)` — validation/normalisation; raises `ValidationError`.
    Requires non-empty `title`/`author`; optional integer `year` (range-checked);
    optional ISBN-10/13 (regex on digit-stripped value); rejects unknown fields.
  - `BookHandler(BaseHTTPRequestHandler)` — routing via `do_GET/POST/PUT/DELETE`,
    `/books/{id}` matched by `BOOK_PATH` regex. JSON I/O helpers `_send`, `_error`,
    `_read_json`, `_validated_body`.
  - `make_server()` / `main()` — bind + serve via `ThreadingHTTPServer`, config
    from `HOST`/`PORT`/`BOOKS_DB` env vars.
- **`tests/test_app.py`** (169 lines) — pytest. Unit tests on `validate_book`,
  integration tests spin up a real server on an ephemeral port against a temp
  SQLite DB; includes a cross-restart persistence test.

## Interfaces / flow

HTTP request → `BookHandler` verb dispatch → path match → (`_validated_body` for
POST/PUT) → `BookStore` SQL → JSON response with status code. Health pings the DB.

## Notes

Framework-free by design (`framework=unknown` in stack.json); the "specified
framework" constraint is satisfied by the stdlib `http.server`.
