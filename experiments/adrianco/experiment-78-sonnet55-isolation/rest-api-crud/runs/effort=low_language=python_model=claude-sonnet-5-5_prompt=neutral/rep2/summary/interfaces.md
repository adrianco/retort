# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` | `app.py:health` |
| POST | /books | `Book \| 400` | `app.py:create` |
| GET | /books | `[Book]` (optional `?author=`) | `app.py:list_books` |
| GET | /books/{id} | `Book \| 404` | `app.py:get_one` |
| PUT | /books/{id} | `Book \| 400 \| 404` | `app.py:update` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:delete` |

## Data schema

`books` table: id (int, pk autoincrement), title (str, not null), author (str, not null), year (int), isbn (str).

## Library API

`create_app(db_path=None)` — Flask app factory; `db_path` falls back to `$BOOKS_DB` then `books.db`.
