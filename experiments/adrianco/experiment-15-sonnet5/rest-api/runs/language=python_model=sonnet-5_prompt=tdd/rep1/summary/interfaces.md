# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `main.py:health_check` |
| POST | /books | `Book` (201) / 422 | `main.py:create_book` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `main.py:list_books` |
| GET | /books/{book_id} | `Book` (200) / 404 | `main.py:get_book` |
| PUT | /books/{book_id} | `Book` (200) / 404 / 422 | `main.py:update_book` |
| DELETE | /books/{book_id} | 204 / 404 | `main.py:delete_book` |

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Request models

- `BookCreate` / `BookUpdate`: `title` (str, min_length=1), `author` (str, min_length=1), `year` (int?), `isbn` (str?)
- `Book` (response): adds `id` (int)
