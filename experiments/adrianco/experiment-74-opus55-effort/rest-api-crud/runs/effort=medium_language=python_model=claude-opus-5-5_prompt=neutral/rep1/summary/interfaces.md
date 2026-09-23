# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.py:do_GET` |
| POST | /books | `Book` (201) / errors (400) | `app.py:do_POST` |
| GET | /books | `[Book]` (200), `?author=` exact case-insensitive filter | `app.py:do_GET` |
| GET | /books/{id} | `Book` (200) / `{"error"}` (404) | `app.py:do_GET` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `app.py:do_PUT` |
| DELETE | /books/{id} | empty (204) / 404 | `app.py:do_DELETE` |

Unknown paths and non-numeric ids return 404.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, optional), `isbn` (TEXT, optional). SQLite via `sqlite3`, one shared connection guarded by a `threading.Lock`.

## Library API

- `BookStore(path)` — `create/list/get/update/delete/close`
- `validate_book(payload)` — returns clean dict or raises `ValidationError`
- `create_server(host, port, db_path)` — returns a `ThreadingHTTPServer`
