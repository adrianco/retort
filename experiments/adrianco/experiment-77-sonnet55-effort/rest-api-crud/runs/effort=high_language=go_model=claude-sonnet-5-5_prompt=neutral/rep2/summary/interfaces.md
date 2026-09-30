# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status,time}` 200 / 503 | `handlers.go:api.health` |
| POST | /books | `Book` 201 (+ Location) / 422 / 400 / 413 | `handlers.go:api.create` |
| GET | /books | `[Book]` 200 (optional `?author=` exact, case-insensitive) | `handlers.go:api.list` |
| GET | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:api.get` |
| PUT | /books/{id} | `Book` 200 / 404 / 422 / 400 | `handlers.go:api.update` |
| DELETE | /books/{id} | 204 / 404 / 400 | `handlers.go:api.delete` |

Routing uses Go 1.22+ `net/http` method+wildcard patterns (`GET /books/{id}`). No third-party web framework.

## Data schema

`books` table (SQLite via `modernc.org/sqlite`, pure-Go): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').

## Library API

`OpenStore(dsn) (*Store, error)`, `Store.{Create,List,Get,Update,Delete,Ping,Close}`, `NewHandler(*Store) http.Handler`.
