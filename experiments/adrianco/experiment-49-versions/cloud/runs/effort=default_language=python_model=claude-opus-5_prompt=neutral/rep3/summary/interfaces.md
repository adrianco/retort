# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, database}` 200/503 | `app.py:health` |
| POST | /books | `Book` 201 (Location hdr) / 400 / 409 | `app.py:create_book` |
| GET | /books | `[Book]` 200 (`?author=` filter) | `app.py:list_books` |
| GET | /books/{id} | `Book` 200 / 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 / 409 | `app.py:update_book` |
| DELETE | /books/{id} | `""` 204 / 404 | `app.py:delete_book` |

All error paths return JSON (`{"error": ..., "details": ...}`) via registered
error handlers, including 404/405 for unknown routes/methods.

## Data schema

`books` table: id (int, pk, autoincrement), title (text, not null),
author (text, not null), year (int, nullable), isbn (text, unique, nullable),
created_at (text), updated_at (text). Index on `author COLLATE NOCASE`.

## Library API

- `create_app(database=None)` — Flask app factory; accepts a DB path so tests
  can use a throwaway SQLite file.
- `validate_book(payload)` — validates/normalizes a payload, raises `ValidationError`.
