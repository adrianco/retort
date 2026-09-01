# Run Summary

**Surface:** A REST API for a book collection (CRUD over `/books`), built with Flask + SQLite, with input validation, author filtering, and a `/health` check.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask app factory, validation, route handlers, error handlers | `create_app()`, `validate_book()`, `register_routes()` |
| `db.py` | SQLite persistence layer (schema, request-scoped connection) | `get_db()`, `init_app()`, `init_db()`, `row_to_dict()` |
| `tests/conftest.py` | pytest fixtures (`client`, `sample_book`) | fixtures |
| `tests/test_books.py` | Integration tests over the API | 14 test functions |

## Interfaces (HTTP routes)

| Method | Path | Description | Success |
|--------|------|-------------|---------|
| GET | `/health` | Liveness + DB check | 200 |
| POST | `/books` | Create a book (title, author, year, isbn) | 201 |
| GET | `/books` | List all books; `?author=` exact case-insensitive filter | 200 |
| GET | `/books/{id}` | Fetch one book | 200 / 404 |
| PUT | `/books/{id}` | Full replace (title+author required) | 200 / 404 |
| PATCH | `/books/{id}` | Partial update (beyond spec) | 200 / 400 / 404 |
| DELETE | `/books/{id}` | Delete a book | 204 / 404 |

## Data schema

`books(id INTEGER PK AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)` + index on `author`.

## Flow

`create_app()` builds the Flask app, wires `db.init_app` (registers teardown + creates the schema), then registers routes and JSON error handlers. Each request opens/reuses a request-scoped SQLite connection via `g`. Writes validate the JSON body through `validate_book()` before touching the DB; reads/deletes go straight to parameterized SQL. All responses are JSON with appropriate status codes.

## Notable qualities

- App-factory pattern with test config injection; DB path overridable via `BOOKS_DB` env.
- Validation covers required fields, type/range checks on `year`, ISBN-10/13 checksum-length check, and unknown-field rejection.
- Parameterized SQL throughout (no injection surface).
- Enhancements beyond spec: PATCH endpoint, 405/415 JSON error handlers, cross-instance persistence test.
