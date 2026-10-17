# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 Book` / `400` | `books_api.py:_create_book` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive) | `books_api.py:_list_books` |
| GET | /books/{id} | `200 Book` / `404` | `books_api.py:_get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `books_api.py:_update_book` |
| DELETE | /books/{id} | `204` / `404` | `books_api.py:_delete_book` |
| GET | /health | `200 {"status":"ok"}` / `503` | `books_api.py:_health` |

Unsupported methods on a known route return `405` with an `Allow` header; bodies over 1 MB return `413`.

## Library API

- `validate_book(data, partial=False)` — validates/cleans a payload; raises `ValidationError`.
- `BookStore(db_path)` — `create / list / get / update / delete / ping / close`.
- `create_server(host, port, db_path)` — builds (does not start) a `ThreadingHTTPServer`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).
