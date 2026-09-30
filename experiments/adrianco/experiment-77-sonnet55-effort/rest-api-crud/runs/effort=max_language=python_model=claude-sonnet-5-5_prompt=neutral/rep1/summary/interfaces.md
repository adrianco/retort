# Interfaces

## HTTP routes

All responses are JSON (including errors), always carry `X-Content-Type-Options: nosniff`, and
`OPTIONS`/`HEAD` are handled generically for every route (204 with `Allow`, and body-less GET).

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status: ok}` 200, or `{status: unavailable}` 503 | `app.py:_health` |
| GET | /books | `[Book]` 200 (optional `?author=` exact, case-insensitive filter) | `app.py:_list_books` |
| POST | /books | `Book` 201 + `Location` header | `app.py:_create_book` |
| GET | /books/{id} | `Book` 200 / 404 | `app.py:_get_book` |
| PUT | /books/{id} | `Book` 200 / 404 (full replace) | `app.py:_update_book` |
| DELETE | /books/{id} | 204 / 404 | `app.py:_delete_book` |

Error statuses emitted: 400 (validation / bad JSON / bad Content-Length / duplicate `author` param),
404, 405 (`Allow` header), 408, 411 (chunked bodies), 413 (>1 MiB body), 500, 503.

## CLI

`bookapi` / `python -m bookapi` — flags `--host` (`BOOKS_HOST`, default 127.0.0.1),
`--port` (`BOOKS_PORT`, default 8000; 0 = pick free), `--db` (`BOOKS_DB`, default `books.db`).
SIGTERM is treated like Ctrl+C for clean shutdown.

## Library API

- `create_app(database=None) -> BookAPI` — WSGI application factory (e.g. `gunicorn 'bookapi:create_app()'`).
- `BookAPI(repository)` — callable WSGI app.
- `BookRepository(database)` — thread-safe CRUD; context-manager; `create/get/list_books/update/delete/ping/close`.
- `validate_book(payload) -> BookData` / `ValidationError(errors)`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-blank CHECK),
`author` (TEXT NOT NULL, non-blank CHECK), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

Validation rules: `title` (<=500) and `author` (<=255) required and non-blank; `year` optional int
in `1..currentYear+1`; `isbn` optional (<=32). Unknown keys (incl. client `id`) ignored; text stripped.
