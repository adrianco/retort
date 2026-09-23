# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, database}` (200 / 503) | `handlers.go:handler.health` |
| POST | /books | `Book` 201 (+ `Location`) / 422 / 400 | `handlers.go:handler.create` |
| GET | /books | `[Book]` 200; `?author=` filter | `handlers.go:handler.list` |
| GET | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:handler.get` |
| PUT | /books/{id} | `Book` 200 / 404 / 422 / 400 | `handlers.go:handler.update` |
| DELETE | /books/{id} | 204 / 404 / 400 | `handlers.go:handler.delete` |

Unknown routes return `404 {"error":"not found"}` and disallowed methods `405 {"error":"method not allowed"}` (Allow header preserved) via `jsonFallback`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').

## Library API

`Store` exposes `Create/List(author)/Get(id)/Update/Delete/Ping/Close`. `List` filters by author with `COLLATE NOCASE` exact match.
