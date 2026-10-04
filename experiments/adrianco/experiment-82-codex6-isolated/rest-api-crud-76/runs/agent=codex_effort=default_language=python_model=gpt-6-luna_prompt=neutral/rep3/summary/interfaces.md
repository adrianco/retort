# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: ok}` | `app.py:67` |
| GET | /books | `200 [Book]` (supports `?author=`) | `app.py:77` |
| POST | /books | `201 Book` / `400 {error}` | `app.py:85` |
| GET | /books/{id} | `200 Book` / `404 {error}` | `app.py:108` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `app.py:110` |
| DELETE | /books/{id} | `204` (no body) / `404` | `app.py:122` |

Unknown paths return `404`; unsupported methods on a known path return `405`.

## Data schema

`books` table (SQLite, auto-created on connect): `id` (int, pk autoincrement),
`title` (text, not null), `author` (text, not null), `year` (int, nullable),
`isbn` (text, nullable).
