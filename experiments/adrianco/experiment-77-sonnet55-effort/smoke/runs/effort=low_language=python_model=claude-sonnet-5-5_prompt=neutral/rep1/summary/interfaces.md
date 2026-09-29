# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:_route` |
| POST | /books | `201 Book \| 400` | `app.py:_route` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `app.py:_route` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:_route` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `app.py:_route` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:_route` |

Unmatched method on a known path returns `405`; unknown path returns `404`.

## Data schema

`books` table (SQLite): `id` (int, pk autoincrement), `title` (text, not null),
`author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).

## Library API

- `create_server(db_path="books.db", host, port)` → `ThreadingHTTPServer`
- `init_db(path)` → connection; `validate(data)` → `(clean, error)`
