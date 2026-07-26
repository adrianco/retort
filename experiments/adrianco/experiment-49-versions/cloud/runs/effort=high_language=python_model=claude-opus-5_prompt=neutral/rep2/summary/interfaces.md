# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, database, version}` | `main.py:health` |
| POST | /books | `Book` (201) | `main.py:create_book` |
| GET | /books | `[Book]` (supports `?author=`, `?limit=`, `?offset=`) | `main.py:list_books` |
| GET | /books/{book_id} | `Book \| 404` | `main.py:get_book` |
| PUT | /books/{book_id} | `Book \| 404` | `main.py:replace_book` |
| PATCH | /books/{book_id} | `Book \| 404` | `main.py:update_book` |
| DELETE | /books/{book_id} | `204 \| 404` | `main.py:delete_book` |
| GET | /openapi.json, /docs | OpenAPI schema (FastAPI built-in) | FastAPI |

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT UNIQUE). Index `idx_books_author` on `author`.

## Validation (models.py)

- `title`, `author` required, whitespace-trimmed, non-blank (400 on violation).
- `year` optional, bounded [1000, next year].
- `isbn` optional, normalised (hyphens/spaces stripped), ISBN-10/13 format check, DB-level UNIQUE (409 on duplicate).
