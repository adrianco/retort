# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.py:BookHandler.do_GET` |
| POST | /books | `Book` (201 + `Location`) | `app.py:BookHandler.do_POST` |
| GET | /books | `[Book]` (200), `?author=` exact/case-insensitive filter | `app.py:BookHandler.do_GET` |
| GET | /books/{id} | `Book` (200) / 404 / 400 non-int id | `app.py:BookHandler.do_GET` |
| PUT | /books/{id} | `Book` (200) / 404 / 422 | `app.py:BookHandler.do_PUT` |
| DELETE | /books/{id} | 204 / 404 | `app.py:BookHandler.do_DELETE` |

Error codes: 400 (malformed JSON / non-integer id), 404 (book or route not found), 405 (method not allowed on `/books` or `/books/{id}`), 422 (validation failed, with per-field `details`).

## Library API (exported symbols)

- `BookStore(db_path=":memory:")` — `create`, `list(author=None)`, `get`, `update`, `delete`, `close`
- `validate_book(data)` — returns a normalised dict; raises `ValidationError`
- `make_server(host, port, db_path)` — builds a `ThreadingHTTPServer` bound to its own `BookStore`

## Data schema

`books` table: `id` (int, pk, autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).
