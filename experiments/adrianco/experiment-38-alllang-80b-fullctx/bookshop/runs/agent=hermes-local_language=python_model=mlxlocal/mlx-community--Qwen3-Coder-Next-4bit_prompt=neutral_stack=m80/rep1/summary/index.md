# Architecture summary

> The registered `run-summary` skill was not available in this session; this is a
> compact hand-written summary of the same shape.

**Stack:** Python · FastAPI · SQLite · pydantic. ~299 source LOC across 3 modules.

## Modules

| File | Role |
|------|------|
| `main.py` | FastAPI app. Defines all 6 routes + `/health`, request validation, HTTP status handling. Opens/closes a SQLite connection per request directly (does not reuse `database.py`'s CRUD helpers). |
| `database.py` | SQLite layer: `get_db_connection`, `init_db` (schema with `title/author NOT NULL`), plus a full set of CRUD helpers (`create_book`, `get_book_by_id`, `update_book`, `delete_book`, `list_books`). The helpers are **unused** by `main.py` — routes issue their own SQL. |
| `models.py` | Pydantic models: `Book`, `BookCreate` (title/author required), `BookUpdate` (all optional). |
| `tests/test_api.py` | 11 `TestClient` tests over a module-scoped `client` fixture backed by `test_books.db`. |

## Request flow

`HTTP → FastAPI route (main.py) → sqlite3 connection → Row → pydantic Book → JSON`.
Startup hook calls `init_db()`. `DATABASE_PATH` env var selects the DB file (`books.db`
default, `test_books.db` in tests).

## Notable structural points

- **Dead code / duplication:** `database.py` implements a complete CRUD API that `main.py`
  never calls — routes re-implement the same SQL inline. Two parallel data layers.
- **No dependency manifest:** deps (`fastapi`, `uvicorn`) are only mentioned in the README;
  there is no `requirements.txt` / `pyproject.toml`.
- **Validation is split:** pydantic enforces required fields (→ 422), while `main.py` adds
  empty-string checks (→ 400). The two disagree on status code (see findings).
