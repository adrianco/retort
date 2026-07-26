# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` 200 | `app.py:health` |
| POST | /books | `Book` 201 / errors 400 | `app.py:create_book` |
| GET | /books | `[Book]` 200 (optional `?author=`) | `app.py:list_books` |
| GET | /books/{id} | `Book` 200 / 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` 200 / 404 / 400 | `app.py:update_book` |
| DELETE | /books/{id} | `""` 204 / 404 | `app.py:delete_book` |

Error handlers registered for 404 and 405 return JSON.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Library API

`create_app(db_path=DEFAULT_DB_PATH)` — application factory; `BOOKS_DB` env var overrides the default DB path.
