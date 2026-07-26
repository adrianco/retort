# Architecture Summary

Single-module Flask application backed by SQLite.

## Modules

- **`app.py`** (154 LOC) — the whole service, exposed via an application factory
  `create_app(database_path=None)`.
  - **Persistence:** `get_db()` opens a per-request `sqlite3` connection stored on
    Flask's `g`, sets `row_factory = sqlite3.Row`, and lazily runs
    `CREATE TABLE IF NOT EXISTS books (...)`. `teardown_appcontext` closes it.
  - **Helpers:** `row_to_dict(row)` serializes a book; `validate_book_payload(data, partial)`
    enforces required `title`/`author` (create) and type checks for `year`/`isbn`.
  - **Routes:** `GET /health`, `POST /books`, `GET /books` (`?author=` filter),
    `GET /books/<int:id>`, `PUT /books/<int:id>` (partial update), `DELETE /books/<int:id>`.
  - **Error handling:** JSON handlers for 404 and 405.
  - **Entry point:** `python app.py` runs the dev server on `PORT` (default 5000).
- **`test_app.py`** (153 LOC) — 15 pytest tests using a temp-file DB fixture and Flask's
  `test_client`, covering health, create (success + validation failures), list (empty +
  author filter), get (found + 404), update (success + 404 + invalid), delete (success + 404),
  and a full CRUD flow.

## Interfaces

REST/JSON over HTTP. Book schema: `{id, title, author, year, isbn}`. Status codes:
201 create, 200 get/list/update, 204 delete, 400 validation, 404 not-found, 405 bad method.

## Flow

Request → route handler → `validate_book_payload` (for writes) → `get_db()` connection →
parameterized SQL → `row_to_dict` → `jsonify` with status code.
