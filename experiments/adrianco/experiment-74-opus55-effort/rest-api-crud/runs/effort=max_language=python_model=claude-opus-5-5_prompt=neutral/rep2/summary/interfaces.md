# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` \| 503 | `app.py:health` |
| POST | /books | `Book` (201, `Location` header) | `app.py:create_book` |
| GET | /books | `[Book]` (optional `?author=`) | `app.py:list_books` |
| GET | /books/{book_id} | `Book` \| 404 | `app.py:get_book` |
| PUT | /books/{book_id} | `Book` \| 404 | `app.py:replace_book` |
| DELETE | /books/{book_id} | 204 \| 404 | `app.py:delete_book` |

All error responses use `application/problem+json` (RFC 9457). Validation
failures are 400, unknown routes 404, unsupported methods 405 (with full
`Allow`), non-JSON bodies 415, oversized bodies 413, DB outages 503.

## CLI

`python -m books_api [--host H] [--port P] [--db FILE]` — also reads
`BOOKS_API_HOST`, `BOOKS_API_PORT`, `BOOKS_API_DB`. Runs uvicorn.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-empty),
`author` (TEXT NOT NULL, non-empty), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Request/response models

- `BookIn` — title, author (required, trimmed, no control chars, ≤500);
  year (StrictInt ≥1, not future, nullable); isbn (≤32, nullable).
- `Book` — id + the above fields, as returned.
