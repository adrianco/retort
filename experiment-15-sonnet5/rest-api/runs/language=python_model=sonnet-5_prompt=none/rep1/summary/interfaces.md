# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status": "ok"}` | `main.py:health` |
| POST | /books | `Book` (201) | `main.py:create_book` |
| GET | /books | `[Book]` (200, optional `?author=`) | `main.py:list_books` |
| GET | /books/{book_id} | `Book \| 404` | `main.py:get_book` |
| PUT | /books/{book_id} | `Book \| 404` | `main.py:update_book` |
| DELETE | /books/{book_id} | `204 \| 404` | `main.py:delete_book` |

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null), `author` (TEXT not null), `year` (INTEGER), `isbn` (TEXT).

## Validation

`BookBase` (Pydantic): `title`/`author` required with `min_length=1` plus a `not_blank` field validator that strips whitespace and rejects blanks (HTTP 422). `year`/`isbn` optional. `?author=` filter does a substring `LIKE %author%` match.
