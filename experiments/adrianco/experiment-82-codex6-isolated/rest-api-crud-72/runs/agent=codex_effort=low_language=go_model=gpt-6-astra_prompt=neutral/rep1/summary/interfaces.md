# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:ok}` 200 / 503 if DB down | `main.go:ServeHTTP` |
| POST | /books | `Book` 201 (+ Location) / 400 / 413 | `main.go:save` (id=0) |
| GET | /books | `[Book]` 200 (`?author=` exact filter) | `main.go:list` |
| GET | /books/{id} | `Book` 200 / 400 / 404 | `main.go:ServeHTTP` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `main.go:save` (id>0) |
| DELETE | /books/{id} | 204 / 400 / 404 | `main.go:ServeHTTP` |

Unsupported methods return 405 with an `Allow` header. All non-204 responses are `application/json`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-empty CHECK), `author` (TEXT NOT NULL, non-empty CHECK), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').

## Library API

`API{db *sql.DB}` implements `http.Handler`; `openDB(path)` opens SQLite and creates the schema.
