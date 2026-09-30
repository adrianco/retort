# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `bookapi.py:Handler._dispatch` |
| POST | /books | `Book` (201) / `400` | `bookapi.py:Handler._dispatch` → `BookStore.create` |
| GET | /books | `[Book]` (200), `?author=` exact filter | `bookapi.py:Handler._dispatch` → `BookStore.list` |
| GET | /books/{id} | `Book` (200) / `404` | `bookapi.py:Handler._dispatch` → `BookStore.get` |
| PUT | /books/{id} | `Book` (200) / `400` / `404` | `bookapi.py:Handler._dispatch` → `BookStore.update` |
| DELETE | /books/{id} | `204` / `404` | `bookapi.py:Handler._dispatch` → `BookStore.delete` |

Unsupported methods on a known path return `405`; unknown paths return `404`.

## Library API

- `validate_book(data)` — returns a cleaned book dict or raises `ValidationError`.
- `BookStore(path)` — SQLite-backed store: `create`, `list`, `get`, `update`, `delete`.
- `make_server(host, port, db_path)` — builds a `ThreadingHTTPServer` with a store-bound handler.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
