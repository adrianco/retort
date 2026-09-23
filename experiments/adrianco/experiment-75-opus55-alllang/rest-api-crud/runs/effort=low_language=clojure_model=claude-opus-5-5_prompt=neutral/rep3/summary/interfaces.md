# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status: "ok"}` (200) | `core.clj:app` GET /health |
| POST | /books | `Book` (201) / errors (400) | `core.clj:app` POST /books |
| GET | /books | `[Book]` (200), `?author=` exact filter | `core.clj:app` GET /books |
| GET | /books/:id | `Book` (200) / error (404) | `core.clj:app` GET /books/:id |
| PUT | /books/:id | `Book` (200) / error (404 / 400) | `core.clj:app` PUT /books/:id |
| DELETE | /books/:id | empty (204) / error (404) | `core.clj:app` DELETE /books/:id |
| * | (any) | `{error: "not found"}` (404) | `route/not-found` |

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER, `isbn` TEXT.

## Library API

- `(make-db path)` → datasource, creates the `books` table if absent.
- `(app db)` → Ring handler built from the routes above.
- `(validate b)` → vector of error strings (empty when valid).
