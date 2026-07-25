# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `api.cpp:register_routes` |
| POST | /books | `Book` 201 / error 400 | `api.cpp:register_routes` |
| GET | /books | `[Book]` 200 (optional `?author=` filter) | `api.cpp:register_routes` |
| GET | /books/{id} | `Book` 200 / `{error}` 404 | `api.cpp:register_routes` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `api.cpp:register_routes` |
| DELETE | /books/{id} | 204 / `{error}` 404 | `api.cpp:register_routes` |

Route `{id}` pattern is `(\d+)`, so non-numeric ids never match (fall through to 404).
A server-wide exception handler maps uncaught exceptions to `500 {error}`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

`BookStore(path)` — opens/creates SQLite DB; `create`, `list(author?)`, `get(id)`,
`update(...)`, `remove(id)`, `healthy()`. All methods mutex-guarded.
