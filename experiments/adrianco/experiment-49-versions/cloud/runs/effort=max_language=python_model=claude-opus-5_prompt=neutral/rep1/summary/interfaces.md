# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, database}` (200 / 503) | `routes.py:health` |
| POST | /books | `Book` (201, `Location` header) | `routes.py:create_book` |
| GET | /books | `[Book]` (200, `X-Total-Count` header); `?author=`, `?limit=`, `?offset=` | `routes.py:list_books` |
| GET | /books/{id} | `Book \| 404` | `routes.py:get_book` |
| PUT/PATCH | /books/{id} | `Book \| 404` (partial update allowed) | `routes.py:update_book` |
| DELETE | /books/{id} | `204 \| 404` | `routes.py:delete_book` |

All errors returned as JSON: `{"error": ..., "details": [...]}` (details only on validation failures).

## Data schema

`books` table (SQLite):
`id` (int, pk autoincrement), `title` (text, NOT NULL, non-empty), `author` (text, NOT NULL, non-empty), `year` (int, nullable, 1..9999), `isbn` (text, nullable), `created_at` (text, iso-8601), `updated_at` (text, iso-8601). Index on `author COLLATE NOCASE`.
