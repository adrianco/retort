# Architecture Summary

Single-module Flask application.

## Modules

- **`app.py`** (183 LoC) — the entire service. Defines the Flask app, a per-request
  SQLite connection helper (`get_db` / `close_db` via `teardown_appcontext`),
  `init_db()` schema bootstrap, and six route handlers.
- **`test_app.py`** (213 LoC) — pytest suite, 17 tests across 6 `Test*` classes.
  Uses a `client` fixture backed by a temporary SQLite file and a `sample_books`
  fixture that seeds three rows.
- **`requirements.txt`** — `flask>=2.3.0`, `pytest>=7.4.0`.
- **`README.md`** — setup, run, per-endpoint reference with curl examples.

## Interfaces (routes)

| Method | Path | Handler | Codes |
|--------|------|---------|-------|
| GET | `/health` | `health_check` | 200 |
| POST | `/books` | `create_book` | 201 / 400 |
| GET | `/books` | `list_books` (`?author=` LIKE filter) | 200 |
| GET | `/books/<int:id>` | `get_book` | 200 / 404 |
| PUT | `/books/<int:id>` | `update_book` | 200 / 400 / 404 |
| DELETE | `/books/<int:id>` | `delete_book` | 200 / 404 |

## Data flow

Request → route handler → `get_db()` (request-scoped `sqlite3.Connection`,
`Row` factory) → parameterized SQL against the `books` table → `jsonify`. The
`books` table (`id` PK autoincrement, `title`/`author` NOT NULL, `year`, `isbn`)
is created idempotently by `init_db()`. All queries are parameterized (no string
interpolation into SQL).

## Notes

- Persistence is a file-backed SQLite DB (`books.db` next to `app.py`); tests
  override `app.config['DATABASE']` to a tempfile.
- Author filter is a substring `LIKE %..%` match, not exact.
