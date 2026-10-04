# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status": "ok"}` (200) | `app.py:BookAPI.dispatch` |
| POST | /books | `Book` (201, `Location` header) / 400 / 409 | `app.py:BookAPI.dispatch` → `BookStore.create` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `app.py:BookAPI.dispatch` → `BookStore.list` |
| GET | /books/{id} | `Book` (200) / 404 | `app.py:BookAPI.dispatch` → `BookStore.get` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 / 409 | `app.py:BookAPI.dispatch` → `BookStore.update` |
| DELETE | /books/{id} | (204) / 404 | `app.py:BookAPI.dispatch` → `BookStore.delete` |

Also: 404 for unknown paths, 405 (with `Allow` header) for unsupported methods, 413 for bodies over 1 MB.

## Library API

- `BookAPI(db_path)` — callable WSGI app.
- `BookStore(path)` — `create`, `list(author=None)`, `get(id)`, `update(id, book)`, `delete(id)`.
- `DuplicateISBN` — raised on unique-ISBN conflict.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT UNIQUE, nullable).
