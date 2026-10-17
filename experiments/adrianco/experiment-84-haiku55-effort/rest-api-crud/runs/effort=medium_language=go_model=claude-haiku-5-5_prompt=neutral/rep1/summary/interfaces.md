# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `server.go:handleHealth` |
| POST | /books | `Book` 201 (+ Location) / 400 / 409 | `server.go:handleCreate` |
| GET | /books | `[Book]` 200, `?author=` filter | `server.go:handleList` |
| GET | /books/{id} | `Book` 200 / 404 / 400 | `server.go:handleGet` |
| PUT | /books/{id} | `Book` 200 / 404 / 400 / 409 | `server.go:handleUpdate` |
| DELETE | /books/{id} | 204 / 404 / 400 | `server.go:handleDelete` |

Routing uses Go 1.22+ method-aware `http.ServeMux` patterns, so unmatched methods return 405 automatically.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER not null), isbn (TEXT not null default ''). Partial unique index `books_isbn_unique` on isbn where isbn <> ''.

## Library API (package main, exported)

`Book`, `BookInput`, `BookInput.Validate`, `Store` + its methods, `OpenStore`, `NewServer`, `ErrNotFound`, `ErrDuplicateISBN`.
