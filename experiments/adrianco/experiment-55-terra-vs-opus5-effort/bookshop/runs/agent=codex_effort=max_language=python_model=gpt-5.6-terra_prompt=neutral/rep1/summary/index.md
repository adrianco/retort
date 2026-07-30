# Architecture Summary

Two-file Flask application backed by SQLite.

## Modules

- **`app.py`** — the entire service.
  - `create_app(test_config)` — application factory. Configures `DATABASE`
    (defaults to `books.sqlite3`, overridable via `BOOKS_DATABASE` or
    `test_config`), registers a `before_request` schema initializer, a
    `teardown_appcontext` connection closer, and a JSON error handler for all
    `HTTPException`s.
  - Routes: `GET /health`, `POST /books`, `GET /books` (with `?author=`
    filter), `GET /books/<int:id>`, `PUT /books/<int:id>`,
    `DELETE /books/<int:id>`.
  - Helpers: `get_db` (per-request connection via `g`, with a special
    long-lived connection for `:memory:`), `init_db`, `find_book`,
    `book_to_dict`, `validated_book_payload` (field validation),
    `validation_error`, `not_found`.
  - Module-level `app = create_app()` plus a `__main__` dev-server guard.

- **`tests/test_app.py`** — pytest suite using a `client` fixture built on a
  per-test `tmp_path` SQLite file: health check, create/list/filter,
  get/update/delete round-trip, and validation rejection.

## Data model

Single `books` table: `id` (PK autoincrement), `title` NOT NULL, `author`
NOT NULL, `year` (int, nullable), `isbn` (text, nullable).

## Request flow

`request → before_request(init_db) → route handler → get_db (sqlite3.Row) →
JSON response`. Validation happens in `validated_book_payload` before any
write; missing/invalid `title`/`author` return `400` with a `details` map.
