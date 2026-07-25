# Architecture Summary

> `run-summary` skill unavailable in this session; concise summary written inline.

## Modules

| File | Role |
|------|------|
| `app/main.py` | Entire application: DB helpers, Pydantic models, all routes |
| `app/__init__.py` | Empty package marker |
| `tests/test_api.py` | 4 async pytest integration tests (all currently failing) |

## Design

- **Framework:** FastAPI with a `lifespan` context manager that calls `init_db()` on startup.
- **Persistence:** raw `sqlite3` (no ORM). DB path from `BOOKS_DB_PATH` env var, default `app/books.db`. One connection opened/closed per request. `books` table: `id` (PK autoincrement), `title`/`author` (NOT NULL), `year`, `isbn`.
- **Models:** `BookBase` → `BookCreate` (input) and `Book` (output, adds `id`). `title`/`author` required; `year`/`isbn` optional.
- **Routes:** `POST /books` (201), `GET /books` (+`?author=` filter), `GET /books/{id}` (404 if absent), `PUT /books/{id}` (404 if absent), `DELETE /books/{id}` (204, 404 if absent), `GET /health` (200).

## Request flow

`request → FastAPI route → get_db_connection() → sqlite3 query → Pydantic model → JSON response`.

## Notable

- Application logic is correct end-to-end (verified by a direct `ASGITransport` probe: all 8 operations return correct status codes).
- The test suite uses httpx's removed `AsyncClient(app=...)` shortcut, so no test executes against the app.
