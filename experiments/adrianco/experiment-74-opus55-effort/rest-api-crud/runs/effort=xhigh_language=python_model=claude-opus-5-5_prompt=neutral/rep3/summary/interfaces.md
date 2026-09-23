# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status, database}` / `503` | `app.py:BookAPI.health` |
| GET | /books | `200 [Book]` (optional `?author=` substring filter) | `app.py:BookAPI.list_books` |
| POST | /books | `201 Book` + `Location` header / `400` / `415` | `app.py:BookAPI.create_book` |
| GET | /books/{id} | `200 Book` / `404` | `app.py:BookAPI.get_book` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `app.py:BookAPI.update_book` |
| DELETE | /books/{id} | `204` / `404` | `app.py:BookAPI.delete_book` |

Unmatched paths → `404`; unsupported methods on a matched path → `405` with an `Allow` header. Oversized bodies → `413`; malformed JSON → `400`.

## CLI

`python -m books_api [--host H] [--port P] [--db PATH]` — env fallbacks `BOOKS_API_HOST`, `BOOKS_API_PORT`, `BOOKS_API_DB`. Handles SIGTERM/Ctrl+C for clean shutdown.

## Library API

`create_app(database=None) -> BookAPI` (WSGI callable, e.g. for gunicorn); `BookAPI`, `BookRepository`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-blank CHECK), `author` (TEXT NOT NULL, non-blank CHECK), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
