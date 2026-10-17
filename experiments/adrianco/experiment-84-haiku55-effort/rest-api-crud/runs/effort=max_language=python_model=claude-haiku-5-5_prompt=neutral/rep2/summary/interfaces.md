# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200, or 503 if DB unreadable | `app.py:health` |
| POST | /books | `Book` 201 + `Location` header, 400 on invalid | `app.py:create_book` |
| GET | /books | `[Book]` 200, optional `?author=` substring filter, 400 on blank filter | `app.py:list_books` |
| GET | /books/{id} | `Book` 200 \| 404 | `app.py:get_book` |
| PUT | /books/{id} | `Book` 200 \| 400 \| 404 (full replace) | `app.py:update_book` |
| DELETE | /books/{id} | 204 \| 404 | `app.py:delete_book` |

Unknown routes return JSON 404; wrong method returns JSON 405 with an `Allow` header; unexpected errors return JSON 500. Validation failures return `{"error": "Validation failed.", "details": {field: message}}`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). A custom deterministic `casefold()` SQL function supports case-insensitive, accent-aware author filtering.

## Library API

- `validation.parse_book(payload) -> dict` — validates/cleans title, author, year, isbn; collects all field errors.
- `validation.parse_author_filter(value) -> str | None` — validates the optional author query param.
- `database.*` — connection-taking CRUD helpers.
