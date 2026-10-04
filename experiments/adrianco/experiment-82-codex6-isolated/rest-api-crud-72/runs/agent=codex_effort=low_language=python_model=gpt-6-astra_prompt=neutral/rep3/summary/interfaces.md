# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` (after a `SELECT 1`) | `app.py:BookAPI.dispatch` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `app.py:BookAPI.dispatch` |
| POST | /books | `201 Book` + `Location` header | `app.py:BookAPI.dispatch` / `read_book` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:BookAPI.dispatch` |
| PUT | /books/{id} | `200 Book \| 404 \| 400` (full replace) | `app.py:BookAPI.dispatch` / `read_book` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:BookAPI.dispatch` |

Error codes: 400 (invalid body/fields), 404 (unknown route/book), 405 (`Allow` header), 413 (>1 MiB body), 415 (non-JSON Content-Type), 500 (DB error). `/books/{id}` matches only `[1-9][0-9]*`.

## Library API

`create_app(database=None)` returns a `BookAPI` WSGI callable; DB path from arg, `BOOKS_DB` env, or `books.sqlite3`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
