# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) / 400 | `BookServer.createBook` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `BookServer.listBooks` |
| GET | /books/{id} | `Book` (200) / 404 / 400 (non-numeric id) | `BookServer.getBook` |
| PUT | /books/{id} | `Book` (200) / 404 / 400 | `BookServer.updateBook` |
| DELETE | /books/{id} | 204 / 404 | `BookServer.deleteBook` |
| GET | /health | `{status: UP\|DOWN}` (200 / 503) | `BookServer.handleHealth` |

Unsupported methods on a known path return 405.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Validation (BookInput)

`title` and `author` required (non-blank); `year` must be 1400–2100 if present; `isbn` must match `[0-9Xx-]{10,17}` if present.
