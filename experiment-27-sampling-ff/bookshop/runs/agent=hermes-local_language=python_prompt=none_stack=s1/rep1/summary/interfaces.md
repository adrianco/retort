# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `app.py:health_check` |
| POST | /books | `Book 201 \| error 400` | `app.py:create_book` |
| GET | /books | `[Book] 200` | `app.py:list_books` |
| GET | /books/{id} | `Book 200 \| error 404` | `app.py:get_book` |
| PUT | /books/{id} | `Book 200 \| error 400 \| error 404` | `app.py:update_book` |
| DELETE | /books/{id} | `{message} 200 \| error 404` | `app.py:delete_book` |

`GET /books` accepts an optional `?author=` query param, matched via SQL `LIKE '%author%'` (substring, case-insensitive).

## CLI commands

(none)

## Library API

(none — module is run as a Flask app via `python app.py`)

## Data schema

`books` table: id (INTEGER, pk, autoincrement), title (TEXT, NOT NULL), author (TEXT, NOT NULL), year (INTEGER, nullable), isbn (TEXT, nullable). Stored in a SQLite file `books.db` co-located with `app.py`; WAL journal mode enabled per connection.
