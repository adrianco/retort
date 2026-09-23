# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, database}` 200 / 503 | `books_api.py:handle_request` |
| POST | /books | `Book` 201 / 400 / 409 | `books_api.py:handle_request` → `BookStore.create` |
| GET | /books | `[Book]` 200 (`?author=` exact, case-insensitive) | `handle_request` → `BookStore.list` |
| GET | /books/{id} | `Book` 200 / 404 | `handle_request` → `BookStore.get` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 / 409 | `handle_request` → `BookStore.update` |
| DELETE | /books/{id} | 204 / 404 | `handle_request` → `BookStore.delete` |

Unsupported methods on known paths return 405; bodies over 1 MiB return 413.

## Library API (exported symbols)

- `BookStore(db_path)` — thread-safe SQLite repository: `create/list/get/update/delete/ping/close`
- `validate_book(data) -> dict` — payload validation, raises `ValidationError`
- `handle_request(store, method, path, body) -> (status, payload)` — framework-independent dispatch
- `make_server(host, port, db_path, quiet)` — `ThreadingHTTPServer`
- Exceptions: `ValidationError`, `ConflictError`

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, unique, nullable).
