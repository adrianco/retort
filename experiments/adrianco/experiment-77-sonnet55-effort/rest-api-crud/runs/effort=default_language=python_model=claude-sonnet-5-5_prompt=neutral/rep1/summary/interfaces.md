# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) / 400 | `app.py:_route` → `store.create` |
| GET | /books | `[Book]` (200), `?author=` filter | `app.py:_route` → `store.list` |
| GET | /books/{id} | `Book` (200) / 404 | `app.py:_route` → `store.get` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `app.py:_route` → `store.update` |
| DELETE | /books/{id} | 204 / 404 | `app.py:_route` → `store.delete` |
| GET | /health | `{"status": "ok"}` (200) | `app.py:_route` |

Unmatched methods on `/books` and `/books/{id}` return 405. Unknown paths return 404.

## Library API

- `create_server(host, port, db_path)` — builds a `ThreadingHTTPServer`.
- `BookStore` — `create`, `list`, `get`, `update`, `delete`.
- `validate(data)` — returns `(clean_data, errors)`.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).
