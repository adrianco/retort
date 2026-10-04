# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:BooksHandler.do_GET` |
| POST | /books | `201 Book` / `400 {error}` | `app.py:BooksHandler.do_POST` |
| GET | /books | `200 [Book]` (optional `?author=` substring filter, case-insensitive) | `app.py:BooksHandler.do_GET` |
| GET | /books/{id} | `200 Book` / `404 {error}` | `app.py:BooksHandler.do_GET` |
| PUT | /books/{id} | `200 Book` / `400 {error}` / `404 {error}` | `app.py:BooksHandler.do_PUT` |
| DELETE | /books/{id} | `204` (no body) / `404 {error}` | `app.py:BooksHandler.do_DELETE` |

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

- `connect(db_path)` — opens a SQLite connection (Row factory) and creates the `books` table if absent.
- `create_handler(db_path)` — returns a `BooksHandler` class bound to that DB path.
- `serve(host, port, db_path)` — runs the threading HTTP server.
