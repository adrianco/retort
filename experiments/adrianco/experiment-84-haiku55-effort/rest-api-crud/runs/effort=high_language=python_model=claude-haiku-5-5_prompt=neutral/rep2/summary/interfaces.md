# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `server.py:_health` |
| GET | /books | `[Book]` 200 (optional `?author=` exact, case-insensitive; blank → 400) | `server.py:_list_books` |
| POST | /books | `Book` 201 + `Location` header / 400 | `server.py:_create_book` |
| GET | /books/{id} | `Book` 200 / 404 | `server.py:_get_book` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `server.py:_replace_book` |
| DELETE | /books/{id} | 204 / 404 | `server.py:_delete_book` |

Cross-cutting: unknown route → 404 JSON; wrong method → 405 with `Allow` header; body > 1 MB → 413 (connection closed); malformed Content-Length → 400; invalid JSON body → 400.

## CLI

`python -m bookapi [--host H] [--port P] [--db FILE]` — starts the threaded HTTP server.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). ISBN stored compact (hyphens/spaces stripped, uppercased).
