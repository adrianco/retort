# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `app.py:health_check` |
| POST | /books | `Book 201 \| 400` | `app.py:create_book` |
| GET | /books | `[Book] 200` (optional `?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `Book 200 \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `Book 200 \| 400 \| 404` | `app.py:update_book` |
| DELETE | /books/{id} | `{message} 200 \| 404` | `app.py:delete_book` |

## Data schema

`books` table (SQLAlchemy model `Book`): id (int, pk), title (str, not null), author (str, not null), year (int, nullable), isbn (str, nullable).

## CLI commands

(none)

## Library API

(none — module runs `app.run()` under `__main__`)
