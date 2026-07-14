# Run Summary: bookshop rest-api-crud (python / hermes-local / stack=s3)

## Surface

A single-service Flask REST API for managing a book collection, backed by SQLite.
Exposes full CRUD over `/books`, an author filter on the list route, and a
`/health` check. One application module plus one test module.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask app: 6 routes, SQLite connection mgmt, schema init, validation | `app`, `get_db()`, `init_db()`, route handlers |
| `test_app.py` | pytest integration tests via Flask test client | 16 test functions across 7 classes |

## Interfaces (HTTP)

| Method | Path | Handler | Codes |
|--------|------|---------|-------|
| GET | `/health` | `health_check` | 200 |
| POST | `/books` | `create_book` | 201 / 400 / 409 |
| GET | `/books` | `list_books` (`?author=` LIKE filter) | 200 |
| GET | `/books/<int:id>` | `get_book` | 200 / 404 |
| PUT | `/books/<int:id>` | `update_book` | 200 / 400 / 404 / 409 |
| DELETE | `/books/<int:id>` | `delete_book` | 200 / 404 |

## Flow

Request → route handler → per-request `sqlite3` connection from Flask `g`
(`get_db`) → parametrized SQL against `books` table → `jsonify` of row dict(s).
`teardown_appcontext` closes the connection. Schema is created at import time via
`init_db()`. Tests swap `app.DATABASE` to a temp file and reinit per fixture.

## Notable characteristics

- Persistence is real SQLite on disk (`books.db`), not in-memory state.
- ISBN has a UNIQUE constraint; duplicate inserts surface as HTTP 409.
- Validation trims and rejects empty `title`/`author`; `year` coerced to int.
- No auth, pagination, or ORM — appropriate to the task scope.
