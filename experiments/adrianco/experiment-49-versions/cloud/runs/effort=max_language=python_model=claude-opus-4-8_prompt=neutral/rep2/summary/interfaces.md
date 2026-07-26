# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) / `{errors}` (400) | `app.py:create_book` |
| GET | /books | `[Book]` (200), `?author=` filter | `app.py:list_books` |
| GET | /books/<int:id> | `Book` (200) / `{error}` (404) | `app.py:get_book` |
| PUT | /books/<int:id> | `Book` (200) / 400 / 404 | `app.py:update_book` |
| DELETE | /books/<int:id> | `{deleted,id}` (200) / 404 | `app.py:delete_book` |
| GET | /health | `{status:ok}` (200) / 500 | `app.py:health` |

Custom JSON error handlers registered for 404 and 405 so all error responses stay JSON.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).
