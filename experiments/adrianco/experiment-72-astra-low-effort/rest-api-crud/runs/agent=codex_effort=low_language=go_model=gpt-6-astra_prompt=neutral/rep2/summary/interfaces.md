# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 Book` + `Location` header | `main.go:API.save` (id==0) |
| GET | /books | `200 [Book]` (supports `?author=` exact match) | `main.go:API.list` |
| GET | /books/{id} | `200 Book \| 400 \| 404` | `main.go:API.get` |
| PUT | /books/{id} | `200 Book \| 404` | `main.go:API.save` (id!=0) |
| DELETE | /books/{id} | `204 \| 404` | `main.go:API.delete` |
| GET | /health | `200 {"status":"ok"} \| 503` | `main.go:API.ServeHTTP` |

Unsupported methods return `405` with an `Allow` header.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, trim>0 CHECK),
`author` (TEXT NOT NULL, trim>0 CHECK), `year` (INTEGER NOT NULL DEFAULT 0),
`isbn` (TEXT NOT NULL DEFAULT '').

## CLI flags

`-addr` (listen address, default `:8080`), `-db` (SQLite path, default `books.db`).
