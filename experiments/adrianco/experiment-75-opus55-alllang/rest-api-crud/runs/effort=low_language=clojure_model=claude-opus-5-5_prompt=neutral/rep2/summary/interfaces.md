# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status: "ok"}` (200) | `core.clj:handler` |
| GET | /books | `[Book]` (200), optional `?author=` exact filter | `core.clj:handler` |
| POST | /books | `Book` (201) / `{errors}` (400) | `core.clj:handler` + `with-valid-body` |
| GET | /books/:id | `Book` (200) / `{error}` (404) | `core.clj:handler` + `find-book` |
| PUT | /books/:id | `Book` (200) / `{errors}` (400) / `{error}` (404) | `core.clj:handler` + `with-valid-body` |
| DELETE | /books/:id | `` (204) / `{error}` (404) | `core.clj:handler` |
| (any) | /* | `{error: "not found"}` (404) | `route/not-found` |

## Data schema

`books` table: id (INTEGER pk, autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER), isbn (TEXT). SQLite file at `DB_PATH` (default `books.db`).

## Library API

- `make-db [path]` — creates datasource + `books` table, returns datasource.
- `app [ds]` — builds the wrapped Ring handler.
- `validate [b]` — returns a vector of error strings (empty = valid).
