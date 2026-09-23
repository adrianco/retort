# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:handleHealth` |
| GET | /books | `[Book]` 200 (optional `?author=` filter) | `handlers.go:handleListBooks` |
| POST | /books | `Book` 201 (+ `Location` header) / 400 | `handlers.go:handleCreateBook` |
| GET | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:handleGetBook` |
| PUT | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:handleUpdateBook` |
| DELETE | /books/{id} | 204 / 404 / 400 | `handlers.go:handleDeleteBook` |

Unmatched paths return JSON 404; unsupported methods on known paths return JSON 405 with an `Allow` header.

## Data schema

`books` table (SQLite, via `modernc.org/sqlite`): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT NOT NULL DEFAULT ''. Index `books_author_idx` on `author COLLATE NOCASE`.

## Library API (package main, exported)

`Book`, `BookInput`, `ValidationError`, `Store`, `OpenStore`, `NewHandler`, `ErrNotFound`.
