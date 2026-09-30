# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: ok}` | `app.py:BookHandler.do_GET` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.py:BookHandler.do_GET` |
| POST | /books | `201 Book \| 400` | `app.py:BookHandler.do_POST` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:BookHandler.do_GET` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `app.py:BookHandler.do_PUT` |
| DELETE | /books/{id} | `200 {deleted: true} \| 404` | `app.py:BookHandler.do_DELETE` |

## Data schema

`books` table: id (int, pk autoincrement), title (text, not null), author (text, not null), year (int, nullable), isbn (text, nullable).
