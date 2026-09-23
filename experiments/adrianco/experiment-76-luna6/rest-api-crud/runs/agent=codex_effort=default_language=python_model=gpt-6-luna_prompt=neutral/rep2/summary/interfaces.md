# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` (200) | `app.py:application` |
| GET | /books | `[Book]` (200) | `app.py:application` |
| GET | /books?author= | `[Book]` filtered (200) | `app.py:application` |
| POST | /books | `Book` (201, `Location` header) | `app.py:application` + `read_book` |
| GET | /books/{id} | `Book` (200) \| 404 | `app.py:application` |
| PUT | /books/{id} | `Book` (200) \| 404 | `app.py:application` + `read_book` |
| DELETE | /books/{id} | empty (204) \| 404 | `app.py:application` |

Other status codes: 400 (invalid JSON / missing title or author), 405 (method not allowed, with `Allow` header), 500 (`sqlite3.Error`).

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable).

## Library API

`create_app(database_path=None)` returns a WSGI application; database path defaults to `$BOOKS_DATABASE` or `books.sqlite3`.
