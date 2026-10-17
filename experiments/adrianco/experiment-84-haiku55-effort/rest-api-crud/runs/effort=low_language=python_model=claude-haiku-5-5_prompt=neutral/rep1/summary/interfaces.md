# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `server.py:_dispatch` |
| POST | /books | 201 `Book` (+ Location) \| 400 | `server.py:_create_book` |
| GET | /books | 200 `[Book]`, optional `?author=` | `server.py:_list_books` |
| GET | /books/{id} | 200 `Book` \| 404 | `server.py:_get_book` |
| PUT | /books/{id} | 200 `Book` \| 400 \| 404 | `server.py:_update_book` |
| DELETE | /books/{id} | 204 \| 404 | `server.py:_delete_book` |

Unmatched method on a known path returns 405 with an `Allow` header; unknown
paths and non-numeric ids return 404; bodies >1 MB return 413.

## Library API

- `BookStore(db_path)` — `create`, `get`, `list(author=)`, `update(partial)`, `delete`, `close`
- `validate_book(data, partial=False)` — normalises/validates input, raises `ValidationError`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
