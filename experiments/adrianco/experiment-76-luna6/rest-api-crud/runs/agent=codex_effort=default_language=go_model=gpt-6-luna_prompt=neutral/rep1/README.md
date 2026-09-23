# Book Collection API

A small REST API for storing books in SQLite. It uses Go's standard HTTP server and the SQLite driver `github.com/mattn/go-sqlite3`.

## Requirements

- Go 1.22 or newer
- CGO enabled and a C compiler (required by the SQLite driver)

## Run

```sh
go mod download
go run .
```

The server listens on port `8080` and creates `books.db` in the current directory. Set `PORT` and `BOOKS_DB_PATH` to change the port and database path.

## API

- `GET /health` — returns `{"status":"ok"}` when the service and database are available.
- `POST /books` — creates a book; JSON body fields are `title`, `author`, `year`, and `isbn`. Title and author must be nonempty. Returns `201 Created` and the created book.
- `GET /books` — returns all books as a JSON array. Add `?author=Name` to filter by exact author name.
- `GET /books/{id}` — returns one book, or `404 Not Found`.
- `PUT /books/{id}` — replaces a book's fields; title and author must be nonempty. Returns the updated book, or `404 Not Found`.
- `DELETE /books/{id}` — removes a book. Returns `204 No Content`, or `404 Not Found`.

Malformed JSON, unknown JSON fields, missing required fields, and invalid IDs return `400 Bad Request`.

## Tests

```sh
go test ./...
```
