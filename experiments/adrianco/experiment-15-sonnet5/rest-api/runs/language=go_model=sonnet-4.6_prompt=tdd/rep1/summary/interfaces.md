# Interfaces

## HTTP routes

Registered via Go 1.22+ method-aware `http.ServeMux` patterns in `handler.go:newRouter`.

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `handler.go:handleHealth` |
| POST | /books | `201 Book` \| `400` | `handler.go:handleCreateBook` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `handler.go:handleListBooks` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `handler.go:handleGetBook` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `handler.go:handleUpdateBook` |
| DELETE | /books/{id} | `204` \| `400` \| `404` | `handler.go:handleDeleteBook` |

## Library API

`store` interface (`store.go`): `create`, `list(author)`, `get(id)`, `update(id, b)`, `delete(id)`, `close`. Implemented by `sqliteStore`.

## Data schema

`books` table (`store.go:newSQLiteStore`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).
