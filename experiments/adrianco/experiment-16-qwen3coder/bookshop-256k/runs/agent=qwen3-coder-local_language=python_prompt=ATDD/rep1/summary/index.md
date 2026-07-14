# Architecture Summary

Single-module Flask REST service for a book collection, backed by SQLite.

## Modules

| File | Role | Notes |
|------|------|-------|
| `app.py` | The service (run target) | Flask app; all 6 CRUD routes + `/health`; `init_db`/`get_db_connection` helpers. This is the file `simple_test.py` launches. |
| `app_clean.py` | Near-duplicate of `app.py` | Adds an unused `clear_all_books()` test-support helper. Not imported or run by anything. Dead/duplicate copy. |
| `simple_test.py` | Integration test | One monolithic `test_api()` that spawns `app.py` as a subprocess and drives it over HTTP (create→list→get→update→delete). |
| `verify_implementation.py` | Static structure checker | Greps `app.py` for endpoint/function strings; `verify_requirements()` always returns `True` without exercising behavior. Not a behavioral test. |
| `books.db` | SQLite store | `books(id, title, author, year, isbn)`; currently empty. |
| `README.md` | Docs | Setup + run + endpoint reference. |

## Interfaces (HTTP)

`POST /books`, `GET /books` (`?author=` filter), `GET /books/{id}`, `PUT /books/{id}`,
`DELETE /books/{id}`, `GET /health`. JSON in/out; status codes 200/201/400/404.

## Flow

Each request opens a fresh `sqlite3` connection (`get_db_connection`), executes
parameterized SQL, and returns `jsonify(...)`. No ORM, no blueprints, no app factory.
`init_db()` runs only under `__main__`, so the schema is created when `app.py` is
executed directly (as the test does).

## Data model

`books` table: `id INTEGER PK AUTOINCREMENT`, `title TEXT NOT NULL`,
`author TEXT NOT NULL`, `year INTEGER`, `isbn TEXT`.
