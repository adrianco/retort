# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `app.py:health` |
| POST | /books | `Book 201 \| 400` | `app.py:create_book` |
| GET | /books | `[Book] 200` (optional `?author=` LIKE filter) | `app.py:list_books` |
| GET | /books/{id} | `Book 200 \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `Book 200 \| 400 \| 404` | `app.py:update_book` |
| DELETE | /books/{id} | `{message} 200 \| 404` | `app.py:delete_book` |

## Data schema

`books` table: id (int, pk, autoincrement), title (text, not null), author (text, not null), year (int, nullable), isbn (text, nullable).

## CLI commands

(none)

## Library API

(none — module runs `init_db()` on import and serves via `app.run()` under `__main__`)
