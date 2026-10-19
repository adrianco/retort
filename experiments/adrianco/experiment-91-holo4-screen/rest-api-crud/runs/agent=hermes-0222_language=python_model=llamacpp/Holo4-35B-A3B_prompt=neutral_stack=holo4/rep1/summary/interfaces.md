# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` 200 | `app.py:health` |
| POST | /books | `Book` 201 / `{error}` 400 | `app.py:create_book` |
| GET | /books | `[Book]` 200 (optional `?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `Book` 200 / `{error}` 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` 200 / `{error}` 400\|404 | `app.py:update_book` |
| DELETE | /books/{id} | `""` 204 / `{error}` 404 | `app.py:delete_book` |

## Data schema

`books` table (SQLite, `books.db`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## CLI commands

(none)

## Library API

(none — single-file Flask app; `init_db()` runs at import time)
