# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` 200 / `{"status":"unavailable"}` 503 | `app.py:_health` |
| GET | /books | `[Book]` 200 (optional `?author=` filter, case-insensitive) | `app.py:_list_books` |
| POST | /books | `Book` 201 + `Location` header / 400 | `app.py:_create_book` |
| GET | /books/{id} | `Book` 200 / 404 | `app.py:_get_book` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `app.py:_update_book` |
| DELETE | /books/{id} | 204 / 404 | `app.py:_delete_book` |

Unsupported methods on a known path return 405 with an `Allow` header; unknown paths return 404; malformed JSON and non-object bodies return 400.

## CLI

`python app.py [--host H] [--port N] [--db PATH]` — starts the server.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

Validation: `title`/`author` required, stripped, ≤500 chars; `year` optional int in [1000, next year]; `isbn` optional, normalized ISBN-10/13 (format only, check digit not verified).
