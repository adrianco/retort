# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` \| `503` | `handlers.go:handleHealth` |
| POST | /books | `201 Book` (Location header) \| `400` | `handlers.go:handleCreateBook` |
| GET | /books | `200 [Book]` (`?author=` filter) | `handlers.go:handleListBooks` |
| GET | /books/{id} | `200 Book` \| `404` \| `400` | `handlers.go:handleGetBook` |
| PUT | /books/{id} | `200 Book` \| `404` \| `400` | `handlers.go:handleUpdateBook` |
| DELETE | /books/{id} | `204` \| `404` \| `400` | `handlers.go:handleDeleteBook` |

Unsupported methods on known paths return `405` with an `Allow` header (JSON body); unknown paths return JSON `404`.

## Data schema

`books` table (SQLite, `modernc.org/sqlite`): id (INTEGER pk AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER default 0), isbn (TEXT default ''), created_at (TEXT RFC3339Nano), updated_at (TEXT RFC3339Nano). Index `idx_books_author` on author COLLATE NOCASE.

## CLI

`bookapi -addr :8080 -db books.db` — flags override env (`ADDR`/`PORT`, `DB_PATH`). `:memory:` supported.
