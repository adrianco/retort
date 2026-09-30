# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` | `app.py:_route` (200) |
| POST | /books | `Book` (201) / `{error}` (400) | `app.py:_route` → `store.create` |
| GET | /books | `[Book]` (200), `?author=` filter | `app.py:_route` → `store.list` |
| GET | /books/{id} | `Book` (200) / `{error}` (404) | `app.py:_route` → `store.get` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `app.py:_route` → `store.update` |
| DELETE | /books/{id} | 204 / 404 | `app.py:_route` → `store.delete` |

Unmatched method on a valid path returns 405; unknown path returns 404.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).
