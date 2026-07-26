# Run Summary

**Surface:** A single-file Flask REST API for managing a book collection, backed by
SQLite. Exposes CRUD routes for `/books`, an `?author=` list filter, and a `/health`
check. Ships with a pytest integration suite and a README.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask app factory, SQLite schema init, all route handlers, validation | `create_app()`, `init_db()`, `get_db()`, `_validate_required()` |
| `test_app.py` | pytest integration tests via `app.test_client()` | 11 test functions, `client` fixture |

## Interfaces

- `create_app(database_path=None) -> Flask` — app factory; DB path from arg,
  `BOOKS_DB` env, or default `books.db`. Enables per-run isolation in tests.
- HTTP surface: `GET /health`, `POST /books`, `GET /books` (+`?author=`),
  `GET/PUT/DELETE /books/<int:book_id>`.
- Validation: `_validate_required()` enforces non-empty string `title`/`author`,
  optional int `year`, optional string `isbn`.

## Flow

Request → route handler → `get_db()` (per-request `g._database` connection,
`sqlite3.Row` factory) → parameterized SQL → `book_to_dict()` → `jsonify` with
status code. Connection closed on `teardown_appcontext`. Schema created idempotently
(`CREATE TABLE IF NOT EXISTS`) at app construction.

## Notes

- Clean app-factory pattern; parameterized queries throughout (no SQL injection).
- Data persists to a SQLite file (satisfies embedded-DB requirement).
- No pagination, auth, or ISBN-uniqueness — none required by the spec.
