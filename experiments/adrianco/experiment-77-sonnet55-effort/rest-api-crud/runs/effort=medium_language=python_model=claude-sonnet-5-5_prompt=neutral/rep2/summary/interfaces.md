# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.py:handle` |
| POST | /books | `Book` (201) | `app.py:handle` → `validate`, INSERT |
| GET | /books | `[Book]` (200), optional `?author=` exact-match filter | `app.py:handle` |
| GET | /books/{id} | `Book` (200) \| 404 | `app.py:handle` → `get_book` |
| PUT | /books/{id} | `Book` (200) \| 404 \| 400 | `app.py:handle` → `validate`, UPDATE |
| DELETE | /books/{id} | (204) \| 404 | `app.py:handle` |

Unknown routes → 404; unsupported methods on a known path → 405. Errors are JSON `{"error": "..."}`.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Library API

`create_app(db_path="books.db")` returns a WSGI `app(environ, start_response)` callable.
