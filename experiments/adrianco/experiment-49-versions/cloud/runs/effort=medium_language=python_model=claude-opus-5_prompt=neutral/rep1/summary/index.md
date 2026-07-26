# Architecture Summary

A small FastAPI + SQLite CRUD service for a book collection. Layered into three modules
under `bookapi/` with a clean separation of routing, validation, and persistence.

## Modules

| Module | Responsibility |
|--------|----------------|
| `bookapi/main.py` | FastAPI app + routes (`/health`, CRUD on `/books`). Owns HTTP status codes, `Location` header on create, and translation of `sqlite3.IntegrityError` (UNIQUE isbn) into 409. Uses a `lifespan` handler to `init_db()` on startup. |
| `bookapi/schemas.py` | Pydantic v2 models. `BookIn` (title/author required, year bounded 1450..now+5, isbn format-checked) and `Book` (adds `id`). `extra="forbid"` + `str_strip_whitespace=True`. Empty-string isbn coerced to `None`. |
| `bookapi/db.py` | `sqlite3` connection handling. `get_conn()` context manager commits on success / rolls back on error. Schema with `books` table (UNIQUE isbn) and an author index. DB path overridable via `BOOKS_DB_PATH`. |
| `bookapi/__init__.py` | Re-exports `app`. |

## Flow

`request → FastAPI route (main.py) → Pydantic validation (schemas.py) → parameterised SQL via get_conn() (db.py) → SQLite → JSON response`

## Interfaces

- `POST /books` → 201 + Location header; 409 on duplicate isbn; 422 on invalid body
- `GET /books?author=` → 200 list, exact-author filter, id-ordered
- `GET /books/{id}` → 200 / 404
- `PUT /books/{id}` → 200 (full replace) / 404 / 409
- `DELETE /books/{id}` → 204 / 404
- `GET /health` → 200 `{"status":"ok"}` (also pings the DB)

## Tests

25 tests across `tests/test_books_api.py` (CRUD, filtering, health, 409) and
`tests/test_validation.py` (required fields, blank/whitespace, year/isbn rules,
unknown-field rejection). Per-test throwaway SQLite DB via a `tmp_path` fixture.
0 skips. test_coverage=0.99.

## Notes

- No ORM — parameterised `sqlite3` queries (all bind params → no injection surface).
- Validation failures surface as HTTP 422 (FastAPI/Pydantic default), not 400.
