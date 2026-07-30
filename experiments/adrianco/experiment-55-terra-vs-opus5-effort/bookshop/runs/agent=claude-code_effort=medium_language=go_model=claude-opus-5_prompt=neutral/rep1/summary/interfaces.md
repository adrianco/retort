# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` / `503` | `server.go:handleHealth` |
| POST | /books | `201 Book` (+ `Location`) / `400` | `server.go:handleCreate` |
| GET | /books | `200 [Book]` (`?author=` filter) | `server.go:handleList` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `server.go:handleGet` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `server.go:handleUpdate` |
| DELETE | /books/{id} | `204` / `400` / `404` | `server.go:handleDelete` |

Routing uses Go 1.22+ method-aware `http.ServeMux` patterns, so unmatched methods
return `405 Method Not Allowed` automatically.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER NOT NULL DEFAULT 0),
`isbn` (TEXT NOT NULL DEFAULT ''). Index `books_author_idx` on `author`.

## Library API

`Store` (persistence): `OpenStore(dsn)`, `Create`, `List(author)`, `Get`, `Update`,
`Delete`, `Ping`, `Close`. `BookInput.toBook()` performs validation, returning a
`*ValidationError` with per-field messages.
