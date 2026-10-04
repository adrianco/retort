# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | 201 `Book` + `Location` header | `main.go:API.save` (id=0) |
| GET | /books | 200 `[Book]` (optional `?author=` exact filter) | `main.go:API.list` |
| GET | /books/{id} | 200 `Book` \| 404 | `main.go:API.get` |
| PUT | /books/{id} | 200 `Book` \| 404 | `main.go:API.save` (id>0) |
| DELETE | /books/{id} | 204 \| 404 | `main.go:API.ServeHTTP` |
| GET | /health | 200 `{"status":"ok"}` \| 503 | `main.go:API.ServeHTTP` |

Unsupported methods return 405 with an `Allow` header; malformed JSON / unknown fields / invalid IDs return 400; bodies over 1 MiB return 413; DB errors return 500.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-empty check), `author` (TEXT NOT NULL, non-empty check), `year` (INTEGER default 0), `isbn` (TEXT default '').

## Configuration

Env vars: `DB_PATH` (default `books.db`), `ADDR` (default `:8080`).
