# Book Collection API

A REST API for managing a book collection, written in Go with the standard
library HTTP router and SQLite storage. The SQLite driver is pure Go
(`modernc.org/sqlite`), so no C compiler is required.

## Requirements

- Go 1.22 or newer (the router uses method-aware patterns such as `GET /books/{id}`)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both can be changed with environment variables:

| Variable   | Default    | Purpose                          |
|------------|------------|----------------------------------|
| `ADDR`     | `:8080`    | Address to listen on             |
| `BOOKS_DB` | `books.db` | Path to the SQLite database file |

Example:

```sh
ADDR=:9000 BOOKS_DB=/tmp/books.db go run .
```

## Test

```sh
go test ./...
```

Tests run against an in-memory SQLite database through the full HTTP handler,
so they exercise routing, validation, status codes, and persistence logic.

## API

All responses are `application/json`. Error responses have the form
`{"error": "..."}`; validation failures also include a `fields` array.

### Book resource

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

Validation rules for create and update:

- `title` is required and must not be blank
- `author` is required and must not be blank
- `year` must be between 0 and next calendar year
- `isbn` is optional
- Unknown fields are rejected
- Request bodies are limited to 1 MiB

### Endpoints

| Method   | Path          | Description                              | Success |
|----------|---------------|------------------------------------------|---------|
| `GET`    | `/health`     | Health check (verifies database access)  | 200     |
| `POST`   | `/books`      | Create a book                            | 201     |
| `GET`    | `/books`      | List all books; `?author=` filters exact | 200     |
| `GET`    | `/books/{id}` | Get one book                             | 200     |
| `PUT`    | `/books/{id}` | Replace a book's fields                  | 200     |
| `DELETE` | `/books/{id}` | Delete a book                            | 204     |

### Status codes

- `400` invalid JSON, validation failure, or malformed ID
- `404` book not found
- `413` request body too large
- `500` unexpected database error
- `503` health check failed

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, filtered by author
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":""}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Project layout

| File             | Contents                                          |
|------------------|---------------------------------------------------|
| `main.go`        | Entry point, configuration, HTTP server           |
| `handlers.go`    | Routes, request decoding, validation, responses   |
| `store.go`       | SQLite schema and data access                     |
| `server_test.go` | HTTP-level tests covering all endpoints           |
