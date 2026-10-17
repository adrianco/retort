# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.py:health` |
| POST | /books | `Book` (201, `Location` header) \| 400 | `app.py:create_book` |
| GET | /books | `[Book]` (200), `?author=` filter | `app.py:list_books` |
| GET | /books/{id} | `Book` (200) \| 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` (200) \| 404 \| 400 | `app.py:update_book` |
| DELETE | /books/{id} | empty (204) \| 404 | `app.py:delete_book` |

Error handlers: `ValidationError` → 400 JSON `{error, details}`; 404 → JSON; 405 → JSON.

## Data schema

`books` table (SQLite): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable).

## Library API

`create_app(db_path=None)` — application factory; `BOOKS_DB_PATH` env var or default `books.db`.
