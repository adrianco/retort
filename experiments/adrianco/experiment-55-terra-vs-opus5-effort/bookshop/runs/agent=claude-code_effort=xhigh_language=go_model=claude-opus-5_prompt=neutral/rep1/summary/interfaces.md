# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status, database}` 200/503 | `handlers.go:handleHealth` |
| POST | /books | `Book` 201 (+Location), 422/400/409/415 | `handlers.go:handleCreateBook` |
| GET | /books | `{books, count}` 200 (`?author=` filter) | `handlers.go:handleListBooks` |
| GET | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:handleGetBook` |
| PUT | /books/{id} | `Book` 200 / 404 / 422 / 409 | `handlers.go:handleUpdateBook` |
| DELETE | /books/{id} | 204 / 404 / 400 | `handlers.go:handleDeleteBook` |

Method-mismatch on any known path returns 405 with an `Allow` header; unknown paths return a JSON 404.

## CLI

`bookapi [-addr :8080] [-db books.db] [-log-level info]` — also reads `BOOKAPI_ADDR`, `BOOKAPI_DB`, `BOOKAPI_LOG_LEVEL`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER default 0), `isbn` (TEXT, partial UNIQUE index where not null), `created_at`/`updated_at` (TEXT RFC3339Nano). Index on `author COLLATE NOCASE`.
