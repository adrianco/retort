# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 | `app.py:do_GET` |
| POST | /books | `Book` 201 / `{error}` 400 | `app.py:do_POST` |
| GET | /books | `[Book]` 200 (optional `?author=`) | `app.py:do_GET` |
| GET | /books/{id} | `Book` 200 / `{error}` 404 | `app.py:do_GET` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `app.py:do_PUT` |
| DELETE | /books/{id} | `{deleted}` 200 / 404 | `app.py:do_DELETE` |

## Data schema

`books` table: id (int, pk autoincrement), title (text, not null), author (text, not null), year (int), isbn (text).

## Library API

`create_server(db_path, host, port)` → `ThreadingHTTPServer`; `init_db(path)` → sqlite3 connection; `validate(data)` → `(book|None, error|None)`.
