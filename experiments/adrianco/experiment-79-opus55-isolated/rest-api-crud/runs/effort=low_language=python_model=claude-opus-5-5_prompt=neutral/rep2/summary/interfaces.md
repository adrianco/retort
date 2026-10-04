# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:_health` |
| POST | /books | `201 Book \| 400` | `app.py:_create_book` |
| GET | /books | `200 [Book]` (`?author=` exact, case-insensitive) | `app.py:_list_books` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:_get_book` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `app.py:_update_book` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:_delete_book` |

Unknown routes → 404; unsupported method on a known route → 405; body > 1 MB → 413;
malformed JSON → 400; uncaught error → 500.

## Data schema

`books` table: `id` (int, pk autoincrement), `title` (text, not null), `author`
(text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Library API

- `validate_book(data)` → cleaned dict or raises `ValidationError(errors)`
- `BookStore(db_path)` → `.create/.list/.get/.update/.delete`
- `make_server(host, port, db_path, quiet)` → `ThreadingHTTPServer`
