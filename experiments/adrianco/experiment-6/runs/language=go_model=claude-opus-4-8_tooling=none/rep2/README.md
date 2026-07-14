# Book Collection API

A small REST API for managing a book collection, written in Go using the
standard library `net/http` router (Go 1.22+ method/path patterns) and a pure-Go
SQLite database driver ([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
no cgo required).

## Requirements

- Go 1.22 or newer (developed with Go 1.26)

## Setup & Run

```bash
# Fetch dependencies
go mod download

# Run the server (defaults: :8080, books.db in the current directory)
go run .
```

Configuration via environment variables:

| Variable  | Default    | Description                                  |
|-----------|------------|----------------------------------------------|
| `ADDR`    | `:8080`    | Address/port to listen on                    |
| `DB_PATH` | `books.db` | SQLite file path (use `:memory:` for in-RAM) |

Example:

```bash
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

To build a binary:

```bash
go build -o bookapi .
./bookapi
```

## API

All request and response bodies are JSON. A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`title` and `author` are required on create and update; `year` and `isbn` are
optional.

| Method   | Path             | Description                          | Success |
|----------|------------------|--------------------------------------|---------|
| `GET`    | `/health`        | Health check                         | 200     |
| `POST`   | `/books`         | Create a book                        | 201     |
| `GET`    | `/books`         | List books (optional `?author=` filter) | 200 |
| `GET`    | `/books/{id}`    | Get one book                         | 200     |
| `PUT`    | `/books/{id}`    | Update a book                        | 200     |
| `DELETE` | `/books/{id}`    | Delete a book                        | 204     |

Error responses use the form `{"error": "message"}` with an appropriate status
code:

- `400 Bad Request` — malformed JSON, unknown fields, or missing `title`/`author`
- `404 Not Found` — no book with the given ID
- `500 Internal Server Error` — unexpected database error

### Examples

```bash
# Create
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all / filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

The test suite (`handlers_test.go`) runs against an in-memory SQLite database
and covers the health check, create/get round-trip, input validation, the
author list filter, update, delete, not-found handling, and malformed-JSON
rejection.

## Project layout

| File                | Purpose                                          |
|---------------------|--------------------------------------------------|
| `main.go`           | Entry point; reads config, wires store + server  |
| `book.go`           | The `Book` model                                 |
| `store.go`          | SQLite-backed CRUD store and schema migration    |
| `handlers.go`       | HTTP routing, handlers, validation, JSON helpers |
| `handlers_test.go`  | Integration tests                                |
```
