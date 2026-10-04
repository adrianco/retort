# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `app.py:health` |
| POST | /books | `201 Book \| 400 \| 409` | `app.py:create_book` |
| GET | /books | `200 [Book]` (optional `?author=`) | `app.py:list_books` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book \| 400 \| 404 \| 409` | `app.py:update_book` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:delete_book` |

Unknown paths return `404`; unsupported methods on a known path return `405` with an `Allow` header.

## Data schema

`books` table: `id` (int, pk, autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, unique, nullable).

## Library API

`create_app(db_path=None)` returns a WSGI application; DB path defaults to `$BOOKS_DB` or `books.db`.
