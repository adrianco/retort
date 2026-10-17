# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201 + `Location`) | `books_api.py:_post` |
| GET | /books | `[Book]` (200, optional `?author=`) | `books_api.py:_get` |
| GET | /books/{id} | `Book \| 404` | `books_api.py:_get` |
| PUT | /books/{id} | `Book \| 404` | `books_api.py:_put` |
| DELETE | /books/{id} | 204 \| 404 | `books_api.py:_delete` |
| GET | /health | `{"status": "ok"}` (200) | `books_api.py:_get` |

Validation failures return 400 with `{"error": "validation failed", "details": [...]}`;
duplicate ISBN returns 409; unknown routes and non-numeric IDs return 404.

## Data schema

`books` table: `id` (int, pk, autoincrement), `title` (text, not null),
`author` (text, not null), `year` (int, nullable), `isbn` (text, unique, nullable).

## Library API

- `BookStore(path)` — `create`, `get`, `list(author=)`, `update`, `delete`, `close`
- `validate_book(payload)` — returns normalised dict or raises `ValidationError`
- `create_server(host, port, db_path)` — builds a `ThreadingHTTPServer` (not started)
