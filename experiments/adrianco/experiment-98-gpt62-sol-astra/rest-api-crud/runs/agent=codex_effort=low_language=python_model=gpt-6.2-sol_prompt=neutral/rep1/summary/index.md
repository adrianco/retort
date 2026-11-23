# Architecture Summary — rest-api-crud (gpt-6.2-sol, codex, low)

> Note: produced inline (the `run-summary` skill was not invoked); concise by design.

## Modules

- **`app.py`** (173 lines) — the entire service, no external dependencies (Python stdlib only).
  - `create_app(database)` — builds the `books` table once at startup, returns a WSGI
    `application(environ, start_response)` callable. One SQLite connection per request
    (`app.py:135`), each wrapped in a transaction via `with ... db`.
  - `handle_books(db, environ, method, book_id)` — routes collection vs. item operations
    (POST/GET list vs. GET/PUT/DELETE by id).
  - `read_book(environ)` — body parsing + validation (JSON object, title/author nonblank
    strings, year int-in-range, isbn string, 64 KiB body cap, UTF-8 check).
  - `APIError` — carries HTTP status; caught in `application` and rendered as JSON `{"error": ...}`.
  - `main()` — argparse CLI (`--database/--host/--port`) + `wsgiref.simple_server`.
- **`test_app.py`** (119 lines) — 5 `unittest.TestCase` methods, each wrapping the app in
  `wsgiref.validate.validator` and driving it through a synthetic WSGI `environ`. Uses a
  `TemporaryDirectory`-backed SQLite file; `test_list_filter_and_persistence` re-instantiates
  the app to prove on-disk persistence.
- **`README.md`** — setup, run, endpoint table, curl examples, test command.

## Interfaces / routes

`GET /health`, `POST /books`, `GET /books` (`?author=` exact match), `GET|PUT|DELETE /books/{id}`.
Method mismatches return 405 with an `Allow` header; unknown paths return 404.

## Flow

WSGI request → path/method dispatch in `application` → (for `/books*`) open connection →
`handle_books` → SQLite CRUD → JSON body + Content-Type/Content-Length headers → response.
Errors propagate as `APIError`/`sqlite3.Error` and become 4xx/500 JSON.
