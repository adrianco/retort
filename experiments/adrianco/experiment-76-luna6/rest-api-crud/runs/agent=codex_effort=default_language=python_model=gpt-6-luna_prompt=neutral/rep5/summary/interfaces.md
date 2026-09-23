# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:61` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `app.py:64` |
| POST | /books | `201 Book` \| `400` | `app.py:70` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:86` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `app.py:90` |
| DELETE | /books/{id} | `204` \| `404` | `app.py:105` |

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT). Defined in `app.py:_connect` (created on demand with `CREATE TABLE IF NOT EXISTS`).

## Library API

- `create_app(database=DEFAULT_DATABASE) -> WSGI callable` — factory returning the application, bound to a SQLite path (`BOOKS_DATABASE` env var, default `books.db`).
