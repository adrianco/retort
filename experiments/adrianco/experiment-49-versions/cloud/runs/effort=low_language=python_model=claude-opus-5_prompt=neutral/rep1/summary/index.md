# Run Summary

**Surface:** A REST API for a book collection (CRUD + author filter + health check), FastAPI over SQLite.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | HTTP server, Pydantic models, route handlers, SQLite access | `app`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health`, `init_db`, `connect` |
| `test_app.py` | API integration tests via `TestClient` | 8 test functions |

## Interfaces

- **Models:** `BookIn` (title, author required + non-blank; year 1–2200; isbn optional), `Book` (adds `id`).
- **Persistence:** `sqlite3` with `Row` factory; `BOOKS_DB` env var overrides the DB path (defaults to `books.db`); table created at app startup via `lifespan`.
- **Routes:** `GET /health`, `POST /books` (201), `GET /books` (`?author=` filter), `GET /books/{id}` (404), `PUT /books/{id}` (404), `DELETE /books/{id}` (204).

## Flow

Request → FastAPI dependency (`get_db` opens a per-request SQLite connection) → handler executes parameterised SQL → commits → returns Pydantic-validated JSON. Missing ids raise `HTTPException(404)` via the shared `_fetch` helper. Validation is enforced by Pydantic before the handler runs (invalid bodies → 422).

## Notes

- Clean separation of validation (Pydantic), persistence (module functions), and routing.
- Per-request connections via `Depends(get_db)` with `closing()` — no shared connection state.
- Parameterised queries throughout — no SQL injection surface.
