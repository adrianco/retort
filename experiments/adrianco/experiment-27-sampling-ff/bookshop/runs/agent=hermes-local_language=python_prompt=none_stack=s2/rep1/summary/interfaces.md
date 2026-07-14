# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `app.py:health` |
| POST | /books | `Book 201 \| error 400` | `app.py:create_book` |
| GET | /books | `[Book] 200` | `app.py:list_books` |
| GET | /books/{id} | `Book 200 \| error 404` | `app.py:get_book` |
| PUT | /books/{id} | `Book 200 \| error 400 \| error 404` | `app.py:update_book` |
| DELETE | /books/{id} | `{message} 200 \| error 404` | `app.py:delete_book` |

Notes:
- `GET /books` supports an optional `?author=` query param, matched with a `LIKE %...%` substring filter.
- `{id}` is typed as `<int:book_id>`; non-integer IDs 404 at the routing layer.

## CLI commands

(none)

## Library API

(none) — a single Flask `app` object; runs on `0.0.0.0:5000` with `debug=True` when executed directly.

## Data schema

`books` table:
- `id` (INTEGER, PK, AUTOINCREMENT)
- `title` (TEXT, NOT NULL)
- `author` (TEXT, NOT NULL)
- `year` (INTEGER, nullable)
- `isbn` (TEXT, UNIQUE, nullable)

Stored in a SQLite file `books.db` alongside `app.py`. Schema created idempotently by `init_db()` (`CREATE TABLE IF NOT EXISTS`), invoked at import time.
