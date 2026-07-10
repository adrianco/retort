# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `app.py:health_check` |
| POST | /books | `Book 201 \| 400 \| 500` | `app.py:create_book` |
| GET | /books | `[Book] 200` (optional `?author=` filter) | `app.py:get_books` |
| GET | /books/{id} | `Book 200 \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `Book 200 \| 400 \| 404` | `app.py:update_book` |
| DELETE | /books/{id} | `{message} 200 \| 404` | `app.py:delete_book` |

## Data schema

`books` table (SQLite, `books.db`): id (int, pk autoincrement), title (text, not null),
author (text, not null), year (int), isbn (text, unique).

## Library API

`(none)` — single-file Flask app, no exported library surface.

## CLI commands

`(none)` — runs as a Flask dev server via `python app.py`.
