# Book Collection API

A small REST API for managing a book collection, written in Go using the
standard library `net/http` router and an embedded SQLite database.
The SQLite driver is pure Go (`modernc.org/sqlite`), so no C toolchain is needed.

## Requirements

- Go 1.22 or newer (the router uses method-and-path patterns such as `GET /books/{id}`)

## Setup

```sh
go mod download
```

## Run

```sh
go run . -addr :8080 -db books.db
```

Flags:

| Flag    | Default    | Description                              |
|---------|------------|------------------------------------------|
| `-addr` | `:8080`    | HTTP listen address                      |
| `-db`   | `books.db` | Path to the SQLite database file (created if missing) |

The server shuts down gracefully on `Ctrl+C` or `SIGTERM`.

## Build and test

```sh
go build -o bookapi .
go test ./...
```

## API

Every response is JSON. Errors have the shape `{"error": "message"}`.

| Method   | Path          | Description                          | Success | Errors                        |
|----------|---------------|--------------------------------------|---------|-------------------------------|
| `POST`   | `/books`      | Create a book                        | `201`   | `400` validation / bad JSON   |
| `GET`    | `/books`      | List books; `?author=` filters       | `200`   |                               |
| `GET`    | `/books/{id}` | Get one book                         | `200`   | `400` bad id, `404` not found |
| `PUT`    | `/books/{id}` | Replace a book's fields              | `200`   | `400`, `404`                  |
| `DELETE` | `/books/{id}` | Delete a book                        | `204`   | `400`, `404`                  |
| `GET`    | `/health`     | Liveness and database check          | `200`   | `503` if the database is down |

### Book fields

| Field    | Type    | Required | Rules                                             |
|----------|---------|----------|---------------------------------------------------|
| `title`  | string  | yes      | Non-blank after trimming whitespace               |
| `author` | string  | yes      | Non-blank after trimming whitespace               |
| `year`   | integer | no       | `1`–`9999`; omit or `0` means not provided        |
| `isbn`   | string  | no       | Valid ISBN-10 or ISBN-13 (hyphens and spaces allowed) |

`id` is assigned by the server and returned in responses.

`PUT` replaces the whole book, so fields you omit are cleared (for example,
omitting `year` sets it back to "not provided").

Unknown JSON fields are rejected with `400`, which catches misspelt field names.
Request bodies are limited to 1 MiB.

### Author filter

`GET /books?author=Frank Herbert` returns only books whose author matches exactly,
ignoring case. Partial matches are not supported. Results are ordered by `id`.
An empty list is returned as `[]`.

## Examples

```sh
# Create
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List, filtered by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# Delete
curl -i -X DELETE http://localhost:8080/books/1

# Health
curl http://localhost:8080/health
```

Validation failure example:

```json
{"error":"validation failed","fields":{"author":"author is required","title":"title is required"}}
```

## Tests

`go test ./...` runs:

- `book_test.go`: validation rules, ISBN check digits, whitespace normalization
- `store_test.go`: SQLite CRUD, author filtering, missing-row handling, persistence across reopen
- `server_test.go`: end-to-end HTTP tests covering the full book lifecycle, validation
  errors, filtering, 404/405 responses, and the health endpoint

## Project layout

```
main.go        entry point, flags, graceful shutdown
server.go      HTTP routes, handlers, JSON helpers
store.go       SQLite persistence and schema migration
book.go        Book model, input validation, ISBN check
*_test.go      tests
```
