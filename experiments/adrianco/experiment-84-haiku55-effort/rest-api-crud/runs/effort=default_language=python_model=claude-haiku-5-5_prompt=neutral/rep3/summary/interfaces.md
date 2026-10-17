# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, database}` · 200/503 | `http_app.py:_health` |
| GET | /books | `[Book]` · 200 (supports `?author=`) | `http_app.py:_list_books` |
| POST | /books | `Book` · 201 (+ Location) / 400 | `http_app.py:_create_book` |
| GET | /books/{id} | `Book` · 200 / 404 | `http_app.py:_get_book` |
| PUT | /books/{id} | `Book` · 200 / 400 / 404 | `http_app.py:_update_book` |
| DELETE | /books/{id} | empty · 204 / 404 | `http_app.py:_delete_book` |

Unknown routes return JSON 404; unsupported methods on a known path return JSON 405 with an `Allow` header. Oversized bodies return 413; malformed/missing JSON returns 400.

## CLI

`python -m bookapi [--host H] [--port P] [--db PATH] [--log-level L]` — also reads `BOOKAPI_HOST`, `BOOKAPI_PORT`, `BOOKAPI_DB`.

## Library API

`create_server(host, port, db_path) -> BookAPIServer`; `BookStore(path)` with `create/get/list/update/delete/ping/close`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
