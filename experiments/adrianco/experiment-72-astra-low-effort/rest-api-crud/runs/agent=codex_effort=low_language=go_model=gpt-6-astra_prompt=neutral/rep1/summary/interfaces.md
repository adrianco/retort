# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` \| `503` | `main.go:ServeHTTP` |
| POST | /books | `201 Book` + Location \| `400` \| `413` | `main.go:save` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `main.go:list` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `main.go:get` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `main.go:save` |
| DELETE | /books/{id} | `204` \| `400` \| `404` | `main.go:delete` |

All routes emit JSON (`application/json`); errors are `{"error": "..."}`. Unsupported
methods return `405` with an `Allow` header.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL,
CHECK non-blank), `author` (TEXT NOT NULL, CHECK non-blank), `year` (INTEGER
DEFAULT 0), `isbn` (TEXT DEFAULT '').

## CLI commands

(none) — configured via `ADDR` and `DB_PATH` environment variables.

## Library API

(none) — `package main`, no exported library surface.
