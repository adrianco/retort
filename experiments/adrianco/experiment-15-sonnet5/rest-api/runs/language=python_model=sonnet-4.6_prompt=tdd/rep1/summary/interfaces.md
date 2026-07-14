# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status": "ok"}` | `app.py:health` |
| POST | /books | `BookOut` (201) | `app.py:create_book` |
| GET | /books | `[BookOut]` (supports `?author=`) | `app.py:list_books` |
| GET | /books/{book_id} | `BookOut \| 404` | `app.py:get_book` |
| PUT | /books/{book_id} | `BookOut \| 404` | `app.py:update_book` |
| DELETE | /books/{book_id} | `204 \| 404` | `app.py:delete_book` |

## Data schema

`books` table: id (int, pk), title (str, not null), author (str, not null), year (int, nullable), isbn (str, nullable).

## Validation

`BookIn` (Pydantic): `title` and `author` required; a `field_validator` rejects
whitespace-only values. Missing/blank required fields → HTTP 422.
