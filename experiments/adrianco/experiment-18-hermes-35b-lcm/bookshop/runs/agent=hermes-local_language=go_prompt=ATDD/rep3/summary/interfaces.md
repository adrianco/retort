# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `server.go:handleHealth` |
| POST | /books | `201 Book \| 400` | `server.go:handleCreateBook` |
| GET | /books | `200 [Book]` (optional `?author=`) | `server.go:handleListBooks` |
| GET | /books/{id} | `200 Book \| 400 \| 404` | `server.go:handleGetBook` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `server.go:handleUpdateBook` |
| DELETE | /books/{id} | `204 \| 400 \| 404` | `server.go:handleDeleteBook` |

## Data schema

`books` table (SQLite): `id` (INTEGER pk autoincrement), `title` (TEXT not null),
`author` (TEXT not null), `year` (INTEGER default 0), `isbn` (TEXT default '').

## Library API (package `main`)

- `Book{ID,Title,Author,Year,ISBN}` with `Validate()` (title + author required)
- `Database` with CRUD + `ListBooksByAuthor`
- `Server` implementing `http.Handler` via `NewServer(*Database)`
