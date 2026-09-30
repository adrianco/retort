# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.py:dispatch` |
| POST | /books | created book (201) / `422` validation / `400` bad JSON | `app.py:create_book` |
| GET | /books | `[Book]` (200), optional `?author=` case-insensitive exact filter | `app.py:list_books` |
| GET | /books/{id} | `Book` (200) / `404` | `app.py:get_book` |
| PUT | /books/{id} | updated book (200) / `422` / `404` | `app.py:update_book` |
| DELETE | /books/{id} | `{"message":"Book deleted"}` (200) / `404` | `app.py:delete_book` |

Wrong method on a known path → `405`; unknown path → `404`; body over 1 MB → `413`.

## Data schema

`books` table: `id` (int, pk, autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Library API

`create_app(db_path=None)` returns a WSGI callable `BookApp`; `validate_book(data)` returns a cleaned dict or raises `HTTPError`.
