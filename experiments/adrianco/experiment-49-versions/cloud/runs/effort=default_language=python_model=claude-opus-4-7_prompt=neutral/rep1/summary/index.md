# Architecture Summary

Single-module Flask + SQLite REST service (`app.py`, 176 LOC).

## Modules

- **`app.py`** — the entire application.
  - `get_db()` / `init_db()` — per-request SQLite connection via Flask `g`, creates the `books` table.
  - `create_app(database_path=None)` — app factory; registers all routes and a teardown handler that closes the connection. Also mutates the module-level `DATABASE` global when a path is passed.
  - `validate_book(title, author, year, isbn)` — shared validation: title/author required non-empty strings; year int if present; isbn string if present.
  - `row_to_book(row)` — serializes a SQLite row to a dict.
- **`test_app.py`** — 12 pytest tests using a temp-file DB fixture and Flask `test_client`.

## Routes

| Method | Path            | Handler        | Codes         |
|--------|-----------------|----------------|---------------|
| GET    | `/health`       | `health`       | 200           |
| POST   | `/books`        | `create_book`  | 201 / 400     |
| GET    | `/books`        | `list_books`   | 200 (`?author=` filter) |
| GET    | `/books/<id>`   | `get_book`     | 200 / 404     |
| PUT    | `/books/<id>`   | `update_book`  | 200 / 400 / 404 |
| DELETE | `/books/<id>`   | `delete_book`  | 204 / 404     |

Plus 404/405 JSON error handlers.

## Flow

Request → route handler → `get_db()` (lazy per-request connection) → parameterized SQL → JSON response. Partial-update PUT merges provided fields over the existing row before re-validating. All SQL uses bound parameters (no injection surface).

## Notes

- Persistence is real SQLite (file path from `BOOKS_DB` env, default `books.db`).
- The `create_app` global-`DATABASE` mutation is a minor smell but functions correctly for the test fixture and single-process serving.
