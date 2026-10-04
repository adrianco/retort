# Book Collection API

A small REST API for managing books, backed by SQLite.

## Requirements

- Go 1.22 or newer
- A C toolchain for the SQLite driver (`github.com/mattn/go-sqlite3`)

## Run

```sh
go run .
```

The service listens on `:8080` and stores data in `books.db` in the current directory. Set `ADDR` to change the listen address or `BOOKS_DB` to choose another SQLite database path.

## API

- `GET /health`
- `POST /books` with JSON fields `title`, `author`, `year`, and `isbn`
- `GET /books` (optionally filter with `?author=...`)
- `GET /books/{id}`
- `PUT /books/{id}` with the same JSON fields as create
- `DELETE /books/{id}`

Title and author are required. Responses use JSON; successful deletion returns `204 No Content`.

## Tests

```sh
go test ./...
```
