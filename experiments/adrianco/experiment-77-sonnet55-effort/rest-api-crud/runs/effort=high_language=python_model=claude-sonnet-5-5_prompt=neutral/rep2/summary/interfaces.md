# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `bookapi.py:Handler._dispatch` |
| POST | /books | `Book` (201) / 400 | `bookapi.py:Handler._dispatch` → `BookStore.create` |
| GET | /books | `[Book]` (200), `?author=` filter | `bookapi.py:Handler._dispatch` → `BookStore.list` |
| GET | /books/{id} | `Book` (200) / 404 | `bookapi.py:Handler._dispatch` → `BookStore.get` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `bookapi.py:Handler._dispatch` → `BookStore.update` |
| DELETE | /books/{id} | 204 / 404 | `bookapi.py:Handler._dispatch` → `BookStore.delete` |

Unsupported methods on known paths return 405; unknown routes return 404;
uncaught errors return 500. HEAD is handled (headers only).

## Library API

- `make_server(host, port, db_path, verbose)` → `ThreadingHTTPServer` with `.store`
- `BookStore(path)` — `create/get/list/update/delete/close`
- `validate_book(payload)` — returns cleaned dict or raises `ValidationError`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
