# Architecture Summary

A minimal FastAPI + SQLite REST service, three source files, clean layering.

## Modules

- **main.py** — FastAPI app. Pydantic models (`BookIn`, `Book`) define the request/response
  schema and validation (`title`/`author` non-blank via `Field(min_length=1)` + a
  `field_validator` that strips whitespace). Routes: `/health`, and full CRUD on `/books`.
  DB is initialised in a `lifespan` context manager.
- **db.py** — SQLite storage layer. A `connect()` contextmanager yields a `sqlite3` connection
  with `Row` factory and commits on exit. Functions: `init_db`, `create_book`, `list_books`
  (optional exact-match `author` filter), `get_book`, `update_book`, `delete_book`. DB path
  from `BOOKS_DB` env var (default `books.db`).
- **test_api.py** — pytest integration tests against `TestClient`, each using a temporary DB
  via `monkeypatch` of `db.DB_PATH`.

## Flow

HTTP request → FastAPI route (main.py) → Pydantic validation → `db.*` function →
parameterised SQL → dict result → `Book` response model serialised to JSON.

## Notes

- Parameterised SQL throughout (no injection surface).
- Clean separation: HTTP/validation in `main.py`, persistence in `db.py`.
- DELETE returns 204 no-body; 404 with `{"detail": ...}` for unknown IDs; 422 for validation.
