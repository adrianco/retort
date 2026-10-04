# Book Collection API

A small REST API for managing a SQLite-backed book collection. It uses Go's standard `net/http` package.

## Requirements

- Go 1.24 or newer
- A C compiler for the SQLite driver (`mattn/go-sqlite3`)

## Run

```sh
go mod tidy
go run .
```

The server listens on `:8080` and creates `books.db` in the current directory. Set `ADDR` to change the listen address or `BOOKS_DB` to change the database file path.

## Endpoints

- `GET /health` — service health
- `POST /books` — create a book; JSON fields: `title`, `author`, `year`, `isbn`
- `GET /books` — list books; optionally filter with `?author=...`
- `GET /books/{id}` — retrieve a book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Title and author are required for create and update. Successful create returns `201`, reads and updates return `200`, successful delete returns `204`, invalid input returns `400`, and missing books return `404`.

## Test

```sh
go test ./...
```
