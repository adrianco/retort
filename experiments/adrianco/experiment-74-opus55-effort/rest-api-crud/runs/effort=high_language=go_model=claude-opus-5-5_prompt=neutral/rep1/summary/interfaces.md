# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status,database}` \| `503` | `handlers.go:handleHealth` |
| POST | /books | `201` + Book + `Location` \| `400` \| `413` | `handlers.go:handleCreate` |
| GET | /books | `200 [Book]` (`?author=` filter) | `handlers.go:handleList` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `handlers.go:handleGet` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` \| `413` | `handlers.go:handleUpdate` |
| DELETE | /books/{id} | `204` \| `400` \| `404` | `handlers.go:handleDelete` |

Routing uses the Go 1.22+ `net/http.ServeMux` method+path patterns, so unmatched
methods return `405` automatically.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT NOT NULL DEFAULT '').

## Library API

`Store` interface: `Create`, `List`, `Get`, `Update`, `Delete`, `Ping`, `Close` —
implemented by `SQLiteStore` over `modernc.org/sqlite` (pure-Go, no cgo).
