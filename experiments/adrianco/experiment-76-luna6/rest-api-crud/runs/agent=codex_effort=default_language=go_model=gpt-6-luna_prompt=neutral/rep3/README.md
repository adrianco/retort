# Book Collection API

A small REST API built with Go's `net/http` package and SQLite.

## Requirements

- Go 1.23 or newer
- A C compiler for the SQLite driver (`github.com/mattn/go-sqlite3`)

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current directory. Set `ADDR` to change the listen address or `BOOKS_DB` to change the SQLite database path.

## API

- `GET /health` — database health check
- `POST /books` — create a book; JSON fields: `title`, `author`, `year`, `isbn`
- `GET /books` — list books, optionally filtered with `?author=...`
- `GET /books/{id}` — get one book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Create and update require nonblank `title` and `author`. Responses use JSON; successful deletion returns `204 No Content`.

## Test

```sh
go test ./...
```
