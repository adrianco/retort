# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.py:health_check` |
| POST | /books | `BookResponse` (201), 422 on invalid | `app.py:create_book` |
| GET | /books | `[BookResponse]` (200), `?author=` filter | `app.py:list_books` |
| GET | /books/{book_id} | `BookResponse` (200) \| 404 | `app.py:get_book` |
| PUT | /books/{book_id} | `BookResponse` (200) \| 404 | `app.py:update_book` |
| DELETE | /books/{book_id} | empty (204) \| 404 | `app.py:delete_book` |

## Data schema

`books` table: id (int, pk, autoincrement), title (text, not null), author (text, not null), year (int, nullable), isbn (text, nullable), created_at (text, not null), updated_at (text, not null).

## Library API

- `init_db()` — creates the `books` table if absent (called at import).
- `get_db()` — opens a SQLite connection (WAL mode, `Row` factory); DB path from `BOOK_DB` env var, default `books.db`.
- Pydantic models: `BookCreate`, `BookUpdate` (partial), `BookResponse`.
