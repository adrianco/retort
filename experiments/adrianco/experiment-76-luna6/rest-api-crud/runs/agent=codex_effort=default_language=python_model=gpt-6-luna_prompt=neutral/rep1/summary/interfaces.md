# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:75` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `app.py:77` |
| POST | /books | `201 Book` \| `400` | `app.py:86` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:101` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `app.py:106` |
| DELETE | /books/{id} | `204` \| `404` | `app.py:116` |

Unmatched paths return `404`; unmatched methods on `/books/{id}` return `405` with an `Allow` header.

## Library API

- `create_app(db_path=None)` — returns a WSGI application; `db_path` falls back to `$BOOKS_DB` then `books.sqlite3`.
- `main()` — serves the app on `$PORT` (default 8000) via `wsgiref.simple_server`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
