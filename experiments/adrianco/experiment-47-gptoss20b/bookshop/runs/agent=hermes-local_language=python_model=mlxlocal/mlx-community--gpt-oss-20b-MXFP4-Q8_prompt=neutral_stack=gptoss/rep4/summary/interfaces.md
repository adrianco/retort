# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status": "ok"}` | `main.py:health` |
| POST | /books | `BookRead` (201) | `main.py:create_book` |
| GET | /books | `[BookRead]` (200, `?author=` filter) | `main.py:list_books` |
| GET | /books/{book_id} | `BookRead \| 404` | `main.py:get_book` |
| PUT | /books/{book_id} | `BookRead \| 404` | `main.py:update_book` |
| DELETE | /books/{book_id} | `204 \| 404` | `main.py:delete_book` |

## Data schema

`books` table: id (int, pk), title (str, not null), author (str, not null), year (int, nullable), isbn (str, nullable).

## Library API

Pydantic schemas: `BookCreate` (title/author required via `Field(..., min_length=1)`), `BookUpdate` (all optional, partial update), `BookRead` (adds `id`).
