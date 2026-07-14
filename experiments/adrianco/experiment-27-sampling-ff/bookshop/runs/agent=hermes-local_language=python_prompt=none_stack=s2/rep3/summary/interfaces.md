# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 200` | `app.py:health_check` |
| POST | /books | `Book \| 201`, `{error} \| 400` | `app.py:create_book` |
| GET | /books | `[Book] \| 200` (optional `?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `Book \| 200`, `{error} \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `Book \| 200`, `{error} \| 400/404` | `app.py:update_book` |
| DELETE | /books/{id} | `{message} \| 200`, `{error} \| 404` | `app.py:delete_book` |

## CLI commands

(none)

## Library API

- `create_app(database_path=None)` — application factory; accepts `':memory:'` for a shared in-memory test DB.

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).
