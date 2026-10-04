# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:route` |
| GET | /books | `200 [Book]` (optional `?author=`, case-insensitive) | `app.py:route` → `BookStore.list` |
| POST | /books | `201 Book` + `Location` header, `400`/`409` | `app.py:route` → `validate_book` → `BookStore.create` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:route` → `BookStore.get` |
| PUT | /books/{id} | `200 Book` \| `400`/`404`/`409` | `app.py:route` → `validate_book` → `BookStore.update` |
| DELETE | /books/{id} | `204` \| `404` | `app.py:route` → `BookStore.delete` |

Unmatched paths return `404 {"error":"Not found"}`; wrong methods return `405` with an `Allow` header. All responses are JSON with `Content-Type: application/json` (except `204`).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT UNIQUE, nullable).

## Library API

`create_app(db_path)` returns a WSGI callable exposing `app.store` (a `BookStore`). `main(argv)` runs a `wsgiref` server with `--host/--port/--db` flags (also `HOST`/`PORT`/`BOOKS_DB` env vars).
