# Architecture Summary

_Note: the `run-summary` skill is not registered as invocable in this session; this is a hand-written summary of the same shape._

## Modules

- **`app.py`** (~200 LOC) — single-module Flask application. Contains the DB
  helpers, schema init, serialization, and all six routes.
- **`test_app.py`** (~290 LOC) — pytest suite, 20 tests, uses a temp-file
  SQLite DB via a `client` fixture that monkeypatches `app.DATABASE`.

## Interfaces (routes)

| Route | Method | Handler | Codes |
|-------|--------|---------|-------|
| `/health` | GET | `health_check` | 200 |
| `/books` | POST | `create_book` | 201/400/409 |
| `/books` | GET | `list_books` | 200 |
| `/books/<id>` | GET | `get_book` | 200/404 |
| `/books/<id>` | PUT | `update_book` | 200/400/404/409 |
| `/books/<id>` | DELETE | `delete_book` | 200/404 |

## Persistence

SQLite via `sqlite3`, file `books.db` co-located with `app.py`. Connection is
request-scoped through Flask's `g` and torn down in `teardown_appcontext`.
Schema: `books(id PK, title NOT NULL, author NOT NULL, year, isbn UNIQUE)`.

## Flow

`init_db()` runs at import to create the table. Each request opens (or reuses)
a per-request connection, executes parameterized SQL, commits on writes, and
serializes `sqlite3.Row` via `book_to_dict`. All queries are parameterized —
no string interpolation into SQL.
