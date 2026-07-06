# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status: ok}` | `main.py:health` |
| POST | /books | `BookOut` (201) / 422 | `main.py:create_book` |
| GET | /books | `[BookOut]` (200), `?author=` filter | `main.py:list_books` |
| GET | /books/{book_id} | `BookOut` (200) / 404 | `main.py:get_book` |
| PUT | /books/{book_id} | `BookOut` (200) / 404 / 422 | `main.py:update_book` |
| DELETE | /books/{book_id} | 204 / 404 | `main.py:delete_book` |

## Data schema

`books` table (SQLite): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL),
author (TEXT NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable).

## Library API

`db.py:Database(path=":memory:" | "books.db")` — connection wrapper with
`create_book / list_books / get_book / update_book / delete_book / close`.
`main.py:create_app(db=None)` — app factory allowing DB injection for tests.
