# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status": "ok"}` | `app.py:_route` |
| GET | /books | 200 `[Book]` (supports `?author=`) | `app.py:_list_books` |
| POST | /books | 201 `Book` + `Location` header \| 400 | `app.py:_create_book` |
| GET | /books/{id} | 200 `Book` \| 404 | `app.py:_get_book` |
| PUT | /books/{id} | 200 `Book` \| 400 \| 404 | `app.py:_update_book` |
| DELETE | /books/{id} | 204 \| 404 | `app.py:_delete_book` |

Unknown paths return 404; unsupported methods return 405 with an `Allow` header. Malformed JSON returns 400; a body over 1 MB returns 413.

## Library API

- `validate_book(payload)` — returns a cleaned book dict or raises `ValidationError`
- `BookStore(db_path)` — `create`, `list(author=)`, `get`, `update`, `delete`, `close`
- `create_server(host, port, db_path, quiet)` — builds a `ThreadingHTTPServer`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).
