# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) / 400 | `app.py:_route` → `BookStore.create` |
| GET | /books | `[Book]` (200), `?author=` filter | `app.py:_route` → `BookStore.list` |
| GET | /books/{id} | `Book` (200) / 404 | `app.py:_route` → `BookStore.get` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `app.py:_route` → `BookStore.update` |
| DELETE | /books/{id} | 204 / 404 | `app.py:_route` → `BookStore.delete` |
| GET | /health | `{"status":"ok"}` (200) | `app.py:_route` |

Unmatched routes → 404; unsupported methods on a known path → 405; malformed JSON → 400; uncaught errors → 500.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable). Backed by SQLite (`:memory:` in tests, file `books.db` by default).
