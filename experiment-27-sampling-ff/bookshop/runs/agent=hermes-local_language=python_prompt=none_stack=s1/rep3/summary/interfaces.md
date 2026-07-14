# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `app.py:health` |
| POST | /books | `Book 201 \| 400` | `app.py:create_book` |
| GET | /books | `[Book] 200` (supports `?author=`) | `app.py:list_books` |
| GET | /books/{id} | `Book 200 \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `Book 200 \| 400 \| 404` | `app.py:update_book` |
| DELETE | /books/{id} | `{message} 200 \| 404` | `app.py:delete_book` |

## Data schema

`books` table: id (int, pk autoincrement), title (text, not null), author (text, not null), year (int), isbn (text). SQLite file `books.db`, WAL journal mode.
