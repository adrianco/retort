# Architecture Summary — bookapi

Flask + stdlib `sqlite3` REST API for a book collection, laid out as an
application-factory package (`run-summary` skill unavailable; summary authored
during evaluation).

## Modules

| Module | Responsibility |
|--------|----------------|
| `app.py` | Entry point. `create_app()` + `app.run()` with HOST/PORT/FLASK_DEBUG env config. |
| `bookapi/__init__.py` | `create_app()` application factory; DB path config (`BOOKS_DB_PATH`); registers JSON error handlers (400/404/405/415→400/500). |
| `bookapi/db.py` | SQLite layer: per-request connection on `g`, `Row` factory, WAL + foreign_keys pragmas, schema with `books` table and partial-unique ISBN index; `init_app` teardown + schema bootstrap. |
| `bookapi/routes.py` | `books` blueprint: `/health`, `POST/GET /books`, `GET/PUT/PATCH/DELETE /books/<int:id>`; serialization, LIKE-escaped author filter, integer `year` filter, 409 on ISBN conflict, `Location` header on create. |
| `bookapi/validation.py` | Pure `validate_book_payload(payload, partial=)`; returns `(values, errors)`, aggregates all field errors; title/author required, year range, ISBN charset/length. |

## Request flow

`app.py` → `create_app()` → blueprint route → `_json_body()` (tolerant JSON
decode) → `validate_book_payload()` → `get_db()` execute + commit → `_serialize()`
→ `jsonify` with status code. Connection closed on app-context teardown.

## Tests

`tests/` split into `test_books_api.py` (HTTP integration via Flask test client),
`test_persistence.py` (SQLite storage layer, restart durability, health-503,
SQL-injection safety), `test_validation.py` (pure validator unit tests).
`conftest.py` gives a per-test throwaway SQLite file and a `make_book` factory.
~87 tests, 0 skipped.
