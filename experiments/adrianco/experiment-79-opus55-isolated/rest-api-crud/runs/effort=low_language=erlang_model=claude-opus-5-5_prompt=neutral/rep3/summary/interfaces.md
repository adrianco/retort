# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `book_api_health_handler:init/2` |
| POST | /books | 201 `Book` (+ `Location` header) / 422 / 400 | `book_api_books_handler:create_book` |
| GET | /books | 200 `[Book]`; `?author=` exact-match filter | `book_api_books_handler:list_books` |
| GET | /books/{id} | 200 `Book` / 404 / 400 (non-numeric or <=0 id) | `book_api_books_handler:get_book` |
| PUT | /books/{id} | 200 `Book` / 404 / 422 / 400 | `book_api_books_handler:update_book` |
| DELETE | /books/{id} | 204 (no body) / 404 / 400 | `book_api_books_handler:delete_book` |

Error codes: 400 (malformed JSON, non-object body, non-numeric id), 404 (unknown id),
405 (method not allowed, with `Allow` header), 413 (body > 1 MB), 422 (validation failed,
with per-field `details`).

## Data schema

DETS table `book_store_table` (type `set`), keyed by integer id. Each row is
`{Id, #{id, title, author, year, isbn}}`. `title`/`author` are non-blank binaries;
`year` is `integer() | null`; `isbn` is `binary() | null`. A `'$next_id'` row holds a
monotonic counter (ids are never reused).

## Library API

`book_store` gen_server: `create/1`, `list/0`, `list/1` (author filter), `get/1`,
`update/2`, `delete/1`, `clear/0`. `book_api_app:port/0` reports the bound port
(useful when configured as `0`).
