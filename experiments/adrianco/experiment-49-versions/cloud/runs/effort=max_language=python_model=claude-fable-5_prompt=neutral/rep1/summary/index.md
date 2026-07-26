# Architecture Summary

Small Flask + SQLite REST API for a book collection. Three source modules plus tests.

## Modules

| File | Role |
|------|------|
| `app.py` | Flask app factory (`create_app`), all routes, payload validation, consistent JSON error shaping, and a global `HTTPException` handler so framework errors (404/405) also return JSON. |
| `db.py` | SQLite plumbing: idempotent `init_db` (schema with `books` table), per-request connection on `flask.g` via `get_db`, and `close_db` teardown. |
| `test_app.py` | pytest integration tests using Flask's test client against a `tmp_path` SQLite file. |

## Design notes

- **App factory pattern** — `create_app(db_path=None)` resolves the DB path from an
  explicit arg → `BOOKS_DB` env var → default beside `app.py`, enabling clean per-test
  isolation (each test gets a fresh temp DB).
- **Request-scoped connections** — one `sqlite3` connection per request, stored on `g`,
  closed by `teardown_appcontext`; `row_factory = sqlite3.Row` for dict-like access.
- **Validation** — `validate_book_payload` enforces required non-empty `title`/`author`,
  integer `year` (rejecting `bool`), string `isbn`, and rejects unknown fields; returns a
  per-field error map used for `400 {"error": "validation failed", "details": {...}}`.
- **PUT is full-replace** — omitted optional fields reset to `NULL`; documented in README.
- **Author filter** — `?author=` is a case-insensitive exact match (`COLLATE NOCASE`).

## Flow

Route handler → `parse_json_object` / `validate_book_payload` → `database.get_db()` SQL →
`book_to_dict` → `jsonify` with explicit status code. Missing rows → 404; invalid input →
400; unknown route/method → JSON 404/405 via the error handler.
