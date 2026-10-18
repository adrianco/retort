# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201` Book + `Location` header / `400` | `handler.go:create` |
| GET | /books | `200` `[Book]` (`?author=` case-insensitive exact filter) | `handler.go:list` |
| GET | /books/{id} | `200` Book / `400` / `404` | `handler.go:get` |
| PUT | /books/{id} | `200` Book / `400` / `404` | `handler.go:update` |
| DELETE | /books/{id} | `204` / `400` / `404` | `handler.go:delete` |
| GET | /health | `200` `{"status":"ok"}` / `503` if DB unreachable | `handler.go:health` |

Error bodies are JSON: `{"error": "..."}`; validation failures add `{"fields": {...}}`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL DEFAULT 0), `isbn` (TEXT NOT NULL DEFAULT '').

## Library API (internal/book)

`Open(dsn) (*Store, error)`, `(*Store).Create/Get/List/Update/Delete/Close/Ping`, `(*Book).Validate()`, `NewHandler(*Store) *Handler`.

## CLI commands

(none — single server binary configured via `ADDR` / `DB_PATH` env vars.)
