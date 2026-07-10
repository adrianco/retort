# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 | `app.py:health_check` |
| POST | /books | `Book` 201 / `{error}` 400 / 500 | `app.py:create_book` |
| GET | /books | `[Book]` 200 (optional `?author=` filter) | `app.py:get_books` |
| GET | /books/{id} | `Book` 200 / 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 / 500 | `app.py:update_book` |
| DELETE | /books/{id} | `{message}` 200 / 404 / 500 | `app.py:delete_book` |

## Data schema

`book` table (SQLAlchemy model `Book`): id (int, pk), title (str, not null), author (str, not null),
year (int, nullable), isbn (str, nullable), created_at (datetime), updated_at (datetime, onupdate).

Persistence: SQLite at `books.db` in the workspace directory.
