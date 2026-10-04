# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:BookHandler.do_GET` |
| POST | /books | `201 Book \| 400` | `app.py:BookHandler.do_POST` |
| GET | /books | `200 [Book]` (optional `?author=`) | `app.py:BookHandler.do_GET` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:BookHandler.do_GET` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `app.py:BookHandler.do_PUT` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:BookHandler.do_DELETE` |

Also returns `405` for known-path/wrong-method, `411` for missing `Content-Length`, `413` for bodies over 1 MB.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Library API

`validate_book(data) -> cleaned dict | raises ValidationError`; `BookStore(db_path)` with `create/list/get/update/delete/close`; `create_server(host, port, db_path, quiet)`.
