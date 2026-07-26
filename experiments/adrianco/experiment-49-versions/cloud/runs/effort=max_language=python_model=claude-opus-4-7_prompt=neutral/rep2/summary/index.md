# Architecture Summary

**Surface:** A REST API for managing a book collection (CRUD over `/books`), backed
by an embedded SQLite database, with input validation and a `/health` probe. Built
with Flask.

## Modules

| File | Role | Key symbols |
|------|------|-------------|
| `app.py` (184 LOC) | Application factory + all routes + persistence | `create_app`, `get_db`/`close_db`/`init_db`, `validate_book`, `book_to_dict` |
| `test_app.py` (212 LOC) | Integration tests via Flask test client | 21 `test_*` functions, `client` fixture (per-test temp SQLite file) |

## Interfaces (HTTP)

| Method | Path | Handler | Codes |
|--------|------|---------|-------|
| GET | `/health` | `health` | 200 |
| POST | `/books` | `create_book` | 201 / 400 |
| GET | `/books` (`?author=`) | `list_books` | 200 |
| GET | `/books/<int:id>` | `get_book` | 200 / 404 |
| PUT | `/books/<int:id>` | `update_book` | 200 / 400 / 404 |
| DELETE | `/books/<int:id>` | `delete_book` | 204 / 404 |
| (any) | unknown route / bad method | error handlers | JSON 404 / 405 |

## Control flow

- **App factory** (`create_app`) configures `DATABASE_PATH` (env-overridable),
  registers `close_db` teardown, and calls `init_db()` inside an app context to
  create the schema idempotently (`CREATE TABLE IF NOT EXISTS`).
- **Per-request DB** is lazily opened and cached on `flask.g`, `Row` factory set,
  closed on teardown.
- **Write paths** (`create_book`, `update_book`) parse JSON with `silent=True`
  (→ 400 on non-JSON), run `validate_book` (title/author required non-empty,
  optional int `year` with bool-rejection, optional str `isbn`), then INSERT/UPDATE
  and re-SELECT to return the canonical row.
- **JSON error handlers** ensure 404/405 also return JSON, not HTML.

## Notes

- Clean, idiomatic Flask app-factory pattern; parameterized SQL throughout (no
  injection surface).
- Tests isolate state with a per-test `tempfile.mkstemp` SQLite file.
