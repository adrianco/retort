# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` 200 | `app.py:health` |
| POST | /books | `Book` 201 + `Location` / 400 / 415 | `app.py:create_book` |
| GET | /books[?author=] | `[Book]` 200 | `app.py:list_books` |
| GET | /books/{id} | `Book` 200 / 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `app.py:update_book` |
| DELETE | /books/{id} | `{"id":N,"deleted":true}` 200 / 404 | `app.py:delete_book` |

## CLI commands

(none) — `python app.py` starts the dev server.

## Library API

`create_app(database_path=None) -> Flask` — DB path from argument, else `BOOKS_DATABASE`, else `books.db`.

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).
