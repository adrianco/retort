# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library (`net/http`) for routing and a pure-Go SQLite driver
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)) for storage — no
CGO required.

## Requirements

- Go 1.22 or newer (uses method-based routing in `net/http.ServeMux`)

## Setup & Run

```bash
# Fetch dependencies
go mod download

# Run the server (defaults: :8080, db file ./books.db)
go run .

# Optional configuration via environment variables:
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

The server creates the SQLite database and schema automatically on first start.

## Running Tests

Tests use an in-memory SQLite database and do not touch disk:

```bash
go test ./...
```

## API

All responses are JSON. Errors are returned as `{"error": "..."}`.

| Method | Path           | Description                          | Success |
|--------|----------------|--------------------------------------|---------|
| GET    | `/health`      | Health check                         | 200     |
| POST   | `/books`       | Create a book                        | 201     |
| GET    | `/books`       | List books (`?author=` filter)       | 200     |
| GET    | `/books/{id}`  | Get one book                         | 200     |
| PUT    | `/books/{id}`  | Update a book                        | 200     |
| DELETE | `/books/{id}`  | Delete a book                        | 204     |

### Book fields

| Field    | Type   | Required | Notes                |
|----------|--------|----------|----------------------|
| `title`  | string | yes      |                      |
| `author` | string | yes      |                      |
| `year`   | int    | no       | defaults to 0        |
| `isbn`   | string | no       | defaults to `""`     |

`title` and `author` must be non-empty (whitespace-only is rejected with `400`).

### Examples

```bash
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}'

# List all
curl -s localhost:8080/books

# Filter by author
curl -s 'localhost:8080/books?author=Donovan'

# Get one
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# Delete
curl -s -X DELETE localhost:8080/books/1 -i
```

## Status codes

- `200 OK` — successful read/update
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — invalid JSON or missing required fields
- `404 Not Found` — book does not exist
- `500 Internal Server Error` — unexpected database error

## Project layout

| File             | Purpose                                       |
|------------------|-----------------------------------------------|
| `main.go`        | Entry point, configuration, server startup    |
| `server.go`      | HTTP handlers, routing, validation            |
| `store.go`       | SQLite-backed data access layer               |
| `server_test.go` | Integration tests against the HTTP handlers   |
