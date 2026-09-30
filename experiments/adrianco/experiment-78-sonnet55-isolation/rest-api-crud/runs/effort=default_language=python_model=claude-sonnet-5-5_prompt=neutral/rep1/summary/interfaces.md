# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:_route` |
| POST | /books | `201 Book` \| `400` | `app.py:_route` → `BookStore.create` |
| GET | /books | `200 [Book]` (optional `?author=`) | `app.py:_route` → `BookStore.list` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:_route` → `BookStore.get` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `app.py:_route` → `BookStore.update` |
| DELETE | /books/{id} | `204` \| `404` | `app.py:_route` → `BookStore.delete` |

Unmatched method on a known path returns `405`; unknown path returns `404`.

## Library API

- `create_server(host, port, db_path)` — builds a `ThreadingHTTPServer`.
- `BookStore(path)` — SQLite-backed CRUD store, thread-locked.
- `validate(data)` — returns `(cleaned, errors)`.

## Data schema

`books` table: `id` (int, pk, autoincrement), `title` (text, not null), `author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).
