# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` \| `503` | `app.py:_health` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.py:_list_books` |
| POST | /books | `201 Book` + `Location` \| `400` | `app.py:_create_book` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:_get_book` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `app.py:_update_book` |
| DELETE | /books/{id} | `204` \| `404` | `app.py:_delete_book` |

HEAD is served as GET-without-body; unmatched methods return `405` with an `Allow` header.

## CLI commands

`bookapi` (`python -m bookapi`): `--host`, `--port`, `--db`, `--log-level`; defaults from `BOOKAPI_HOST`/`BOOKAPI_PORT`/`BOOKAPI_DB` env vars.

## Library API

`create_app(database) -> BookApp` (WSGI callable); `BookRepository` with `create_book`/`get_book`/`list_books`/`update_book`/`delete_book`/`ping`/`close`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-blank CHECK), `author` (TEXT NOT NULL, non-blank CHECK), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
