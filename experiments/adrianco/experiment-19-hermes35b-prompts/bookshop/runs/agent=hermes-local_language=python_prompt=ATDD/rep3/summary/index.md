# Architecture Summary — bookshop (hermes-local, python, ATDD, rep3)

Small FastAPI CRUD service, 3 source modules (445 LOC total).

## Modules

- **`models.py`** (74 LOC) — Persistence + API contract.
  - `BookModel` — SQLAlchemy ORM table `books` (id, title, author, year, isbn, created_at, updated_at).
  - `init_db()` / `delete_db()` — create/reset the SQLite file `books.db`.
  - Pydantic schemas: `BookCreate` (title/author required, `min_length=1`), `BookUpdate` (all optional), `BookResponse`.
  - Engine: `sqlite:///books.db` with `check_same_thread=False`.

- **`app.py`** (143 LOC) — FastAPI application + routes.
  - `GET /health`, `POST /books`, `GET /books` (with `?author=` filter), `GET /books/{id}`, `PUT /books/{id}`, `DELETE /books/{id}`.
  - Helpers `_now_iso()`, `_book_to_response()`.
  - Per-request `Session(engine)` context managers.

- **`test_app.py`** (228 LOC) — 20 acceptance tests via FastAPI `TestClient`, grouped by endpoint. `autouse` fixture resets the DB between tests.

## Flow

HTTP request → Pydantic validation → route handler opens a `Session` → SQLAlchemy query/commit → `BookResponse` serialized to JSON.

## Notes

- Tests exercise the system only through the public REST API (ATDD-conformant).
- No README.md shipped.
- Uses some deprecated APIs (`Session.query().get()`, `@app.on_event`, `datetime.utcnow()`).
