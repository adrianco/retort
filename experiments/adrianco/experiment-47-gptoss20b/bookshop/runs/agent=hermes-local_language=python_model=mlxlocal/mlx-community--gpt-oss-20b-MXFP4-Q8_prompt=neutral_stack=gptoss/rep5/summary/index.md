# Run Summary

Flask + SQLAlchemy REST API for a book collection, backed by SQLite (`books.db` in cwd).
A single application module (`main.py`) defines the ORM model, DB engine, and all routes.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.py` | Flask app: ORM `Book` model, SQLite engine, all route handlers | `app`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health` |
| `models.py` | **Unused** duplicate model layer (SQLAlchemy `BookModel` + Pydantic schemas) — not imported by `main.py` | `BookModel`, `Book`, `BookCreate`, `BookUpdate`, `Base` |
| `tests/test_api.py` | Flask test-client integration tests | 2 test functions (`test_health`, `test_crud_book`) |

## Interfaces (HTTP routes)

| Method | Path | Description | Codes |
|--------|------|-------------|-------|
| GET | `/health` | Health check → `{"status":"ok"}` | 200 |
| POST | `/books` | Create book (title, author, year, isbn); validates title+author | 201 / 400 |
| GET | `/books` | List books, optional `?author=` filter | 200 |
| GET | `/books/{id}` | Get one book | 200 / 404 |
| PUT | `/books/{id}` | Update fields | 200 / 404 |
| DELETE | `/books/{id}` | Delete book | 204 / 404 |

## Data schema

`books` table: `id` (PK, autoincrement), `title` (not null), `author` (not null), `year` (int), `isbn` (str).

## Flow

Each request opens a scoped session via `SessionLocal()`, performs the query/mutation,
commits where needed, and closes the session. Validation is inline in `create_book`.
`models.py` is dead code left over from an earlier (FastAPI-style, Pydantic v1) attempt.
