# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status": "ok"}` / 503 | `app.py:health` |
| POST | /books | `Book` (201, `Location` header) / 400 | `app.py:create_book` |
| GET | /books | `[Book]` (optional `?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `Book` / 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` / 404 / 400 | `app.py:update_book` |
| DELETE | /books/{id} | 204 / 404 | `app.py:delete_book` |

HEAD is answered by the GET handler (body dropped). Unmatched methods return 405 with an `Allow` header; unmatched paths return 404. Errors are JSON `{"error": ...}` with optional `details`.

## CLI

`python -m bookapi` / `bookapi` — flags `--host` (env `BOOKS_HOST`), `--port` (env `BOOKS_PORT`, 0 = free port), `--db` (env `BOOKS_DB`).

## Library API

`create_app(database=None) -> BookApp` — WSGI-callable factory. `BookRepository` — CRUD API (`create`, `get`, `list_books`, `update`, `delete`, `ping`, `close`).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
