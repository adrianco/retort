# Book Collection API

A small REST API for managing a book collection, written in Go using the standard library
`net/http` router (Go 1.22+ method/path patterns) and SQLite via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver. No CGO needed.

## Requirements

- Go 1.22 or newer

## Setup and run

```sh
go mod download
go run .                       # listens on :8080 and stores data in ./books.db
```

Configuration comes from environment variables:

| Variable  | Default    | Description                 |
|-----------|------------|-----------------------------|
| `ADDR`    | `:8080`    | Address to listen on        |
| `DB_PATH` | `books.db` | SQLite database file path   |

To build a binary instead: `go build -o bookapi . && ./bookapi`

## Endpoints

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| GET    | `/health`     | Health check (also pings the database)       | 200     |
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; `?author=` filters (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                      | 200     |
| DELETE | `/books/{id}` | Delete a book                                | 204     |

Book body:

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

Validation rules:
- `title` and `author` are required (and can't be blank).
- `year` is optional; if you give one, it must be between 0 and next year.
- `isbn` is optional; if you give one, it must have 10 or 13 digits. Hyphens and spaces are allowed, and an ISBN-10 may end in `X`.
- Unknown fields and malformed JSON are rejected.

Error responses are JSON:

```json
{ "error": "validation failed", "fields": { "title": "title is required" } }
```

Status codes: `400` for malformed JSON or a bad id, `404` when the book doesn't exist,
`422` when validation fails, and `500` for unexpected errors.

### Examples

```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
```

## Tests

```sh
go test ./...
```

The tests run the full HTTP handler stack against a temporary SQLite database. They cover
the health check, the create/read/update/delete lifecycle, the author filter, validation and
error status codes, persistence after reopening the database, and ISBN validation.

## Layout

- `main.go`: server startup, configuration and graceful shutdown
- `handlers.go`: HTTP routing, JSON handling and validation
- `store.go`: the SQLite data access layer
- `main_test.go`: integration and unit tests
