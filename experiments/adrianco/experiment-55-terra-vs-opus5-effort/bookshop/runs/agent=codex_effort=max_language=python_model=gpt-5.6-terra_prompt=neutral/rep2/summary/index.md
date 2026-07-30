# Run Summary

## Surface

A Flask REST API for a book collection, backed by SQLite. Exposes full CRUD over
`/books` (create, list with `?author=` filter, read-by-id, update, delete) plus a
`/health` check. JSON responses with appropriate status codes and input validation.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | HTTP server, route handlers, SQLite access, validation | `app`, `create_app()` |
| `tests/test_api.py` | API integration tests | 5 test functions (one parametrized ×3) |

## Interfaces / Routes

| Method | Route | Handler | Notes |
|--------|-------|---------|-------|
| GET | `/health` | `health` | `{"status":"ok"}` |
| POST | `/books` | `create_book` | 201 on success, 400 on invalid payload |
| GET | `/books` | `list_books` | optional `?author=` (case-insensitive exact) |
| GET | `/books/<int:id>` | `read_book` | 200 / 404 |
| PUT | `/books/<int:id>` | `update_book` | full replace; 400 / 404 |
| DELETE | `/books/<int:id>` | `delete_book` | 204 / 404 |

Error handlers registered for 404 and 405 return JSON.

## Control flow

`create_app()` builds a Flask app with an app-factory pattern, configures the DB
path (overridable via `test_config` or `BOOKS_DATABASE` env var), and runs
`init_db()` to create the `books` table on startup. Per-request SQLite connections
are stored on Flask's `g` and closed on teardown. Payload validation is centralized
in `validate_book_payload()` (shared by POST and PUT), raising
`PayloadValidationError` → 400.

## Persistence

SQLite via stdlib `sqlite3`. Single `books` table with autoincrement id and
`NOT NULL` on title/author. Row factory returns dict-like rows serialized to JSON.
