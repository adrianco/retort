# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.py:handle` |
| POST | /books | `Book` (201) / `{"error"}` (400) | `app.py:handle` |
| GET | /books | `[Book]` (200), optional `?author=` exact-match filter | `app.py:handle` |
| GET | /books/{id} | `Book` (200) / `{"error"}` (404) | `app.py:handle` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `app.py:handle` |
| DELETE | /books/{id} | empty (204) / 404 | `app.py:handle` |

All routes return `application/json` (DELETE returns 204 with empty body). Unknown method on a known path → 405; unknown path → 404.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

`create_app(db_path=None)` → WSGI application. `db_path` defaults to `$BOOKS_DB` or `books.db`; `":memory:"` uses a single shared connection.
