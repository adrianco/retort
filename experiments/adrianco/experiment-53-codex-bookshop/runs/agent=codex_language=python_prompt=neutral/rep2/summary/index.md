# Architecture Summary

Single-module Flask application (`app.py`, 169 LOC) backed by SQLite via the stdlib
`sqlite3` module. No ORM.

## Modules

- **`app.py`** — application factory `create_app(test_config=None)` registers all routes
  and returns a configured `Flask` app. A module-level `app = create_app()` provides the
  WSGI entrypoint. Database path is configurable via `DATABASE` config / `DATABASE_PATH`
  env var.
- **`tests/test_api.py`** — 4 pytest integration tests using a per-test tmp SQLite file.

## Interfaces (routes)

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/health` | `health` | returns `{"status": "ok"}` |
| POST | `/books` | `create_book` | validates, inserts, returns 201 + body |
| GET | `/books` | `list_books` | `?author=` filter, case-insensitive (`COLLATE NOCASE`) |
| GET | `/books/<int:id>` | `get_book` | 404 if absent |
| PUT | `/books/<int:id>` | `update_book` | full replace; 404 if absent |
| DELETE | `/books/<int:id>` | `delete_book` | 204; 404 if absent |

## Data flow

Per-request connection via Flask `g` (`get_db`), `sqlite3.Row` row factory, closed on
`teardown_appcontext`. Schema (`books` table) created idempotently at app startup
(`init_db`, `CREATE TABLE IF NOT EXISTS`).

## Validation

`_validate_book` enforces required non-empty `title`/`author`, and type-checks optional
`year` (int, rejects bool) and `isbn` (str). Non-object JSON bodies rejected with 400.
