# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` / `503` | `app.py:_health` |
| GET | /books | `200 [Book]` (optional `?author=`) | `app.py:_list_books` |
| POST | /books | `201 Book` + `Location` / `400` | `app.py:_create_book` |
| GET | /books/{id} | `200 Book` / `404` | `app.py:_get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `app.py:_update_book` |
| DELETE | /books/{id} | `204` / `404` | `app.py:_delete_book` |

Unmatched paths → `404`; wrong method on a known path → `405` with `Allow`. `HEAD` is served as `GET` without a body.

## CLI

`bookapi [--host H] [--port P] [--db FILE]` (env: `BOOKS_HOST`, `BOOKS_PORT`, `BOOKS_DB`).

## Library API

- `BookAPI(store)` — WSGI callable.
- `BookStore(path)` — `create/list/get/update/delete/ping/close`.
- `validate_book(payload) -> (book, errors)`.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable). Index on `author COLLATE NOCASE`.
