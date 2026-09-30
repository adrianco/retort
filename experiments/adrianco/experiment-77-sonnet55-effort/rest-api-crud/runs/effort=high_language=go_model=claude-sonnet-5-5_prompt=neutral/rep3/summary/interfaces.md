# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` 200 / 503 | `handlers.go:health` |
| POST | /books | `Book` 201 (+ `Location`) / 400 / 422 | `handlers.go:createBook` |
| GET | /books | `[Book]` 200 (optional `?author=` exact match) | `handlers.go:listBooks` |
| GET | /books/{id} | `Book` 200 / 400 / 404 | `handlers.go:getBook` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 / 422 | `handlers.go:updateBook` |
| DELETE | /books/{id} | 204 / 400 / 404 | `handlers.go:deleteBook` |

Errors are JSON `{"error":"..."}`. Uses Go 1.22+ `net/http` method-pattern routing (`"POST /books"`, `"GET /books/{id}"`).

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').

## Library API

Exported: `Book`, `Store` (+ `NewStore`, `Create`, `List`, `Get`, `Update`, `Delete`, `Ping`, `Close`), `NewHandler`, `ErrNotFound`.

## CLI commands

(none — single server binary configured via `ADDR` and `DB_PATH` env vars.)
