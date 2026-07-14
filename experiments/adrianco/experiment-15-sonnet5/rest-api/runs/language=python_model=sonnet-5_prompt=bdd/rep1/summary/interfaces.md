# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status": "ok"}` | `main.py:health_check` |
| POST | /books | `Book` (201) | `main.py:create_book` |
| GET | /books | `[Book]` (200), optional `?author=` substring filter | `main.py:list_books` |
| GET | /books/{book_id} | `Book \| 404` | `main.py:get_book` |
| PUT | /books/{book_id} | `Book \| 404` | `main.py:update_book` |
| DELETE | /books/{book_id} | `204 \| 404` | `main.py:delete_book` |

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Request/response models (Pydantic)

- `BookCreate` / `BookUpdate`: `title` (str, min_length=1, non-blank), `author` (str, min_length=1, non-blank), `year` (int?), `isbn` (str?).
- `BookResponse`: the above plus `id` (int).
