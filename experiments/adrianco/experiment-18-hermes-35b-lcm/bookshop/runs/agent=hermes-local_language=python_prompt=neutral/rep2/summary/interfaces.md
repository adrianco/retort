# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `app.py:health_check` |
| POST | /books | `Book 201 \| 400 \| 500` | `app.py:create_book` |
| GET | /books | `[Book] 200` (optional `?author=` partial match) | `app.py:list_books` |
| GET | /books/{id} | `Book 200 \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `Book 200 \| 404 \| 400` | `app.py:update_book` |
| DELETE | /books/{id} | `{message} 200 \| 404` | `app.py:delete_book` |

## CLI commands

(none)

## Library API

(none — single-module Flask app)

## Data schema

`books` table: id (int, pk, autoincrement), title (text, not null), author (text, not null), year (int), isbn (text).
