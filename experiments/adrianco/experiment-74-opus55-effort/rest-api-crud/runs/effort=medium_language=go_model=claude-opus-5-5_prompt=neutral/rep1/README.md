# Book Collection API

A small REST service for managing books, written in Go using the standard library
`net/http` router (Go 1.22+ method/path patterns) and SQLite via the pure-Go
driver [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) (no CGO needed).

## Requirements

- Go 1.25 or newer (required by the SQLite driver)

## Setup and run

```sh
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` by default. Override with
environment variables:

| Variable  | Default    | Description                 |
|-----------|------------|-----------------------------|
| `ADDR`    | `:8080`    | Listen address              |
| `DB_PATH` | `books.db` | SQLite database file path   |

To build a binary: `go build -o bookapi . && ./bookapi`

## Tests

```sh
go test ./...
```

Tests run against an in-memory SQLite database and exercise every endpoint through the HTTP handler.

## API

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check (pings the database)        | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books; `?author=` filters (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get a book                               | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                  | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Book body:

```json
{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
```

Validation: `title` and `author` are required (non-blank); `year` is optional and must be
between 0 and next year; `isbn` is optional and must have 10 or 13 digits (hyphens/spaces
allowed, ISBN-10 may end in `X`). Unknown fields are rejected.

Errors are JSON: `{"error": "..."}`; validation errors also include a `fields` map.
Status codes: `400` invalid input or ID, `404` not found, `405` wrong method, `500` server error.

### Examples

```sh
curl -i -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl localhost:8080/books?author=Frank%20Herbert
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```
