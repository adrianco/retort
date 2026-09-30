# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `main.go:19` (inline) |
| POST | /books | `201 Book \| 400` | `main.go:server.create` |
| GET | /books | `200 [Book]` (opt `?author=`) | `main.go:server.list` |
| GET | /books/{id} | `200 Book \| 404 \| 400` | `main.go:server.get` |
| PUT | /books/{id} | `200 Book \| 404 \| 400` | `main.go:server.update` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `main.go:server.delete` |

Errors are JSON `{"error": "..."}`. Uses Go 1.22+ method-scoped mux patterns (`GET /books/{id}`) and `r.PathValue("id")`.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER default 0), isbn (TEXT default '').

## Library API

`Store` methods: `Create(*Book)`, `List(author string) []Book`, `Get(id) *Book`, `Update(*Book)`, `Delete(id)`, `Close()`. `Update`/`Delete` return `sql.ErrNoRows` for a missing id via the `affected()` helper.
