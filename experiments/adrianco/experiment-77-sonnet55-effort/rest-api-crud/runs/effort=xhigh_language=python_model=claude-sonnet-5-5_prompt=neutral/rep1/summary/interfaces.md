# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` / `503 {status:unavailable}` | `app.py:_health` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive filter) | `app.py:_list_books` |
| POST | /books | `201 Book` + `Location` header / `400` | `app.py:_create_book` |
| GET | /books/{id} | `200 Book` / `404` | `app.py:_get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` (partial update) | `app.py:_update_book` |
| DELETE | /books/{id} | `204` / `404` | `app.py:_delete_book` |

HEAD is served as GET with the body dropped. Unknown paths → JSON `404`; wrong method on a known path → `405` with an `Allow` header; oversized body → `413`; unhandled errors → JSON `500` without leaking details.

## CLI

`python -m bookapi [--host H] [--port P] [--db PATH]` — starts a threaded WSGI server. Env fallbacks: `HOST`, `PORT`, `BOOKS_DB_PATH`.

## Library API

- `create_app(db_path=":memory:") -> BookApp` — build the WSGI callable.
- `BookRepository(path)` — `create/get/list_books/update/delete/ping/close`.
- `validate_book(payload, *, partial=False) -> (fields, errors)`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT). A custom `casefold()` SQL function provides Unicode-aware case-insensitive author matching.
