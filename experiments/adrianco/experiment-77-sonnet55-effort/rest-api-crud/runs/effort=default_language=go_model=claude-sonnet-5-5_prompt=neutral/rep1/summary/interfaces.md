# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` \| `503 {"status":"unhealthy"}` | `main.go:server.health` |
| POST | /books | `201 Book` + `Location` header \| `400` | `main.go:server.create` |
| GET | /books | `200 [Book]` (optional `?author=` exact match) | `main.go:server.list` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `main.go:server.get` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `main.go:server.update` |
| DELETE | /books/{id} | `204` (no body) \| `400` \| `404` | `main.go:server.delete` |

Errors are JSON `{"error": "<message>"}`; unexpected store errors return `500`.

## CLI commands

(none) — the binary takes no flags. Configuration is by environment: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Library API

(none) — single `package main`.

## Data schema

`books` table: `id` INTEGER PRIMARY KEY AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER NOT NULL DEFAULT 0, `isbn` TEXT NOT NULL DEFAULT ''.

`Book` JSON: `{"id": int, "title": string, "author": string, "year": int, "isbn": string}`.
