# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) / 400 | `app.py:handle` (POST branch) |
| GET | /books | `[Book]` (200), `?author=` filter | `app.py:handle` (GET branch) |
| GET | /books/{id} | `Book` (200) / 404 | `app.py:handle` (id GET branch) |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `app.py:handle` (id PUT branch) |
| DELETE | /books/{id} | 204 / 404 | `app.py:handle` (id DELETE branch) |
| GET | /health | `{"status": "ok"}` (200) | `app.py:handle` (health branch) |

Unsupported methods on a known path return 405. Unknown paths return 404.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
