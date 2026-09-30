# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `app.py:dispatch` |
| POST | /books | `201 Book \| 400` | `app.py:create_book` |
| GET | /books | `200 [Book]` (opt `?author=`) | `app.py:list_books` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `app.py:update_book` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:delete_book` |

Non-matching methods on known paths return `405`; unknown paths return `404`. Errors are JSON `{"error": ..., "details": {...}}`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Library API

`create_app(db_path=None) -> BookApp` — WSGI callable; DB path also configurable via `BOOKS_DB` env var.
