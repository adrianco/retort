# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` | `main.py:health_check` |
| POST | /books | `Book` (201) | `main.py:create_book` |
| GET | /books | `[Book]` | `main.py:read_books` (optional `?author=`) |
| GET | /books/{book_id} | `Book \| 404` | `main.py:read_book` |
| PUT | /books/{book_id} | `Book \| 404` | `main.py:update_book` |
| DELETE | /books/{book_id} | `{message} \| 404` | `main.py:delete_book` |

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, NOT NULL), `author` (text, NOT NULL), `year` (int, nullable), `isbn` (text, nullable).

## Library API

Pydantic models: `Book`, `BookCreate`, `BookUpdate`. Helpers: `init_db()`, `get_book_by_id()`, `get_books()`.
