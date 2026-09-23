# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, database}` 200 / 503 | `app.py:health` |
| GET | /books | `[Book]` 200 (optional `?author=` substring, case-insensitive) | `app.py:list_books` |
| POST | /books | `Book` 201 + `Location` / 400 / 413 | `app.py:create_book` |
| GET | /books/{id} | `Book` 200 / 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 (full replace) | `app.py:update_book` |
| DELETE | /books/{id} | 204 / 404 | `app.py:delete_book` |

HEAD is auto-supported for GET routes; unsupported methods return 405 with an `Allow` header. Unknown paths return a JSON 404. `{id}` is constrained to 1–19 digits by the route regex.

## CLI commands

`python -m books_api [--host H] [--port P] [--db PATH]` — runs the threaded server; env fallbacks `BOOKS_API_HOST`/`PORT`/`DB`; SIGTERM/SIGINT trigger clean shutdown.

## Library API

- `create_app(database=None) -> BooksApp` — build the WSGI app (env `BOOKS_API_DB`, default `books.db`).
- `BooksApp(repository, max_body_bytes=1MiB)` — the WSGI callable.
- `BookRepository(database=":memory:")` — CRUD store.
- `validate_book(payload) -> BookData` / `ValidationError`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-blank CHECK), `author` (TEXT NOT NULL, non-blank CHECK), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
