# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: ok}` / `503 {status: unavailable}` | `app.py:_health` |
| POST | /books | `201 Book` + `Location` header / `400` | `app.py:_create_book` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive filter) | `app.py:_list_books` |
| GET | /books/{id} | `200 Book` / `404` | `app.py:_get_book` |
| PUT | /books/{id} | `200 Book` (full replace) / `400` / `404` | `app.py:_update_book` |
| DELETE | /books/{id} | `204` / `404` | `app.py:_delete_book` |

Notes:
- Unknown routes return `404`; wrong methods return `405` with an `Allow` header.
- Trailing slashes are stripped before routing.
- Request bodies are capped at 1 MiB (`413` if exceeded); malformed/missing/non-object JSON returns `400`.
- Responses are `application/json; charset=utf-8` with an explicit `Content-Length`.

## Library API

- `create_app(db_path="books.db") -> BookApp` — build the WSGI app.
- `BookApp(store)` — WSGI callable.
- `BookStore(path)` — `.create/.list_books/.get/.update/.delete/.ping/.close`.
- `validate_book(payload) -> dict` — raises `ValidationError(errors: dict[field, message])`.

## CLI

`python -m bookapi` / `bookapi` console script. Flags: `--host` (env `HOST`, default `127.0.0.1`), `--port` (env `PORT`, default `8000`), `--db` (env `BOOKS_DB`, default `books.db`).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

Validation rules: `title`/`author` required non-empty strings (max 255 chars, trimmed); `year` optional int in 1–9999 (bool rejected); `isbn` optional string (max 32 chars). A custom `CASEFOLD` collation gives Unicode-aware case-insensitive author filtering.
