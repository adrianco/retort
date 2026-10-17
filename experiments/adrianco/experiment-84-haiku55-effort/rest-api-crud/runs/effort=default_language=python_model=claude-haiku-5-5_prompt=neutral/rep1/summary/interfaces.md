# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `books_api.py:_dispatch` (health branch) |
| POST | /books | `201 Book` + `Location` \| 400 | `books_api.py:_create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `books_api.py:_list_books` |
| GET | /books/{id} | `200 Book` \| 404 | `books_api.py:_get_book` |
| PUT | /books/{id} | `200 Book` \| 400 \| 404 | `books_api.py:_update_book` |
| DELETE | /books/{id} | `204` \| 404 | `books_api.py:_delete_book` |

Unknown paths → 404; unsupported methods → 405 with an `Allow` header.

## Library API

- `create_server(host, port, db_path) -> ThreadingHTTPServer`
- `BookStore` — `create/get/list/update/delete` repository over SQLite
- `validate_book(payload, *, partial=False) -> dict` / `ValidationError`

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).
