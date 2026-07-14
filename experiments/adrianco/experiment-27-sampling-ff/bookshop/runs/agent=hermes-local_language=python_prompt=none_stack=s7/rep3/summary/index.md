# Run Summary: bookshop rest-api-crud (python / hermes-local / s7 / rep3)

## Surface

A Flask + SQLite REST API for a book collection. Full CRUD over `/books`
(create, list with `?author=` filter, get-by-id, update, delete) plus a
`/health` check. JSON in/out with conventional HTTP status codes and
title/author input validation.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask app factory, route handlers, SQLite access | `create_app()`, `init_db()`, `get_db()`, 6 view functions |
| `test_app.py` | pytest integration tests via Flask test client | `client`/`sample_books` fixtures, 18 test methods in 6 classes |

## Interfaces

- `create_app(test_db_path=None)` — application factory; registers routes, wires
  `teardown_appcontext`, calls `init_db()`. Accepts an override DB path for tests.
- `get_db()` / `teardown_db()` — per-request connection stored on Flask `g`,
  `sqlite3.Row` factory, WAL journal mode.
- Routes: `GET /health`, `POST /books`, `GET /books`, `GET /books/<int:id>`,
  `PUT /books/<int:id>`, `DELETE /books/<int:id>`.

## Control flow

Request → view function → `get_db()` (opens/returns request-scoped connection)
→ parameterized SQL against the `books` table → `jsonify(...)` with status code.
Connection is closed on app-context teardown. Schema is created idempotently at
`create_app()` time via `CREATE TABLE IF NOT EXISTS`.

## Notes

- Test isolation: each test gets a fresh `tempfile.mkstemp` DB passed through the
  factory; teardown unlinks it.
- Test DB override works by mutating the module-global `DATABASE` inside
  `create_app()` — functional but a shared-mutable-state smell (see findings).
