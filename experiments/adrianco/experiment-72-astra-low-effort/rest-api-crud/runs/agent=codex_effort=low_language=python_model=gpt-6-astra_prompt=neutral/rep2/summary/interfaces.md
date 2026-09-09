# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status: ok}` (200) / 503 | `app.py:dispatch` (health branch) |
| POST | /books | `Book` (201, `Location` header) / 400 / 413 / 415 | `app.py:dispatch` + `read_book` |
| GET | /books | `[Book]` (200), optional `?author=` exact filter | `app.py:dispatch` |
| GET | /books/{id} | `Book` (200) / 404 | `app.py:dispatch` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `app.py:dispatch` + `read_book` |
| DELETE | /books/{id} | `{deleted: id}` (200) / 404 | `app.py:dispatch` |

Unmatched routes → 404; unsupported methods → 405 with an `Allow` header.

## Library API

- `create_app(database=None)` → `BookAPI` WSGI callable (defaults to `BOOKS_DB` env or `books.db`).
- `BookAPI(database)` — WSGI application object; creates the `books` table on init.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
