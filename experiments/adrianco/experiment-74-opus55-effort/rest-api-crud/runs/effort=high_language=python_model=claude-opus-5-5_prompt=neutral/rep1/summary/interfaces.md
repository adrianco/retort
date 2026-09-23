# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status, database}` / `503` | `app.py:health` |
| POST | /books | `201 Book` (+ `Location`) / `400` / `409` | `app.py:create_book` |
| GET | /books | `200 [Book]` (`?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `200 Book` / `404` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` / `409` | `app.py:update_book` |
| DELETE | /books/{id} | `204` / `404` | `app.py:delete_book` |

Unknown paths → 404; wrong method on a known path → 405 with an `Allow` header. Trailing slashes are normalised.

## Data schema

`books` table (SQLite): `id` (int, pk, autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, unique, nullable). Index `idx_books_author` on `author COLLATE NOCASE`.

## Library API

`create_app(db_path=":memory:") -> BooksApp` (WSGI callable); `BookRepository(path)` with `create/list/get/update/delete/ping/close`.

## CLI

`python -m books_api [--host HOST] [--port PORT] [--db PATH]` (env: `BOOKS_HOST`, `BOOKS_PORT`, `BOOKS_DB`).
