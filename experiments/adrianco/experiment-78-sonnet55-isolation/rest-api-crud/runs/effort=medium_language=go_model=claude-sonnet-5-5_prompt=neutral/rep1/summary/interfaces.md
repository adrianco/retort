# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `main.go:routes` (inline) |
| POST | /books | `201 Book` \| `400 {error}` | `main.go:API.create` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `main.go:API.list` |
| GET | /books/{id} | `200 Book` \| `400` \| `404 {error}` | `main.go:API.get` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404 {error}` | `main.go:API.update` |
| DELETE | /books/{id} | `204` \| `400` \| `404 {error}` | `main.go:API.delete` |

Uses Go 1.22+ `net/http` method-and-pattern routing (`"POST /books"`, `"GET /books/{id}"`). Errors returned as JSON `{"error": "..."}`. POST sets a `Location` header.

## Data schema

`books` table (SQLite via `modernc.org/sqlite`, pure-Go): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').

## Library API

`Store` type with `NewStore(dsn)`, `Close()`, and CRUD methods returning a sentinel `errNotFound` on absent rows.
