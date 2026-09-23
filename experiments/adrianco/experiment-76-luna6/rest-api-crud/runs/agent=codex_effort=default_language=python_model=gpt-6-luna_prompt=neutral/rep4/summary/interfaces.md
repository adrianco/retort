# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `app.py:health` |
| POST | /books | `Book` (201) \| 400 | `app.py:create_book` |
| GET | /books | `[Book]` (200), `?author=` filter | `app.py:list_books` |
| GET | /books/{id} | `Book` (200) \| 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` (200) \| 400 \| 404 | `app.py:update_book` |
| DELETE | /books/{id} | `""` (204) \| 404 | `app.py:delete_book` |

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## Library API

`create_app(database_path=None)` — application factory; database path from arg, `BOOKS_DATABASE` env, or `books.db` beside the module.
