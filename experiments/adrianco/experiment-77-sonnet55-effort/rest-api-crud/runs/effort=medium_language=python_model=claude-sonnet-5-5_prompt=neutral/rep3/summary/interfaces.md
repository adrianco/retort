# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) / 400 | `app.py:handle` (POST branch) |
| GET | /books | `[Book]` (200), `?author=` filter | `app.py:handle` (GET list branch) |
| GET | /books/{id} | `Book` (200) / 404 | `app.py:handle` (BOOK_PATH GET) |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `app.py:handle` (BOOK_PATH PUT) |
| DELETE | /books/{id} | (204) / 404 | `app.py:handle` (BOOK_PATH DELETE) |
| GET | /health | `{"status": "ok"}` (200) | `app.py:handle` (health branch) |

Unsupported methods on a known path return 405; unknown paths return 404. Errors are JSON `{"error": "..."}`.

## Library API

- `create_app(db_path=None)` → WSGI callable
- `connect(db_path)` → sqlite3 connection with schema bootstrap
- `validate(data)` → cleaned book dict, raises `ValidationError`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).
