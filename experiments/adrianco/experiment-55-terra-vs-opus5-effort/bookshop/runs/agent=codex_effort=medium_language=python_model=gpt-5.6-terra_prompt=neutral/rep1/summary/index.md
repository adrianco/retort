# Codebase Summary

`run-summary` skill unavailable in this environment; brief manual summary below.

## Modules

- **`app.py`** (160 LoC) — single-module Flask application.
  - `create_app(database_path=None)` — app factory; configures SQLite path from
    arg / `BOOKS_DATABASE` env / `books.db` default, initializes schema, registers routes.
  - Routes: `GET /health`, `POST /books`, `GET /books` (with `?author=` filter),
    `GET /books/<int:id>`, `PUT /books/<int:id>`, `DELETE /books/<int:id>`.
  - Helpers: `get_db`/`init_db` (per-request `g` connection with `Row` factory),
    `book_dict`, `fetch_book`, `validated_book_payload` (title/author required,
    year int, isbn str), `not_found`.
  - Module-level `app = create_app()` plus `__main__` runner.
- **`test_app.py`** (51 LoC) — 3 pytest tests using a `tmp_path` SQLite fixture and
  Flask test client.

## Data flow

Request → route handler → `validated_book_payload()` (for writes) → parameterized
SQLite query via per-request connection → JSON response with appropriate status code
(201/200/204/400/404).

## Persistence

SQLite via stdlib `sqlite3`, schema `books(id, title, author, year, isbn)` created at
app init. Connection stored on Flask `g`, closed on teardown.
