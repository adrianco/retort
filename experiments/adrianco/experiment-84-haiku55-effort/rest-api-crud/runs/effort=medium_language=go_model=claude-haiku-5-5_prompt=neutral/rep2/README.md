# Book Collection API

A small REST service for managing a book collection, written in Go using only
the standard library HTTP router and SQLite for storage. No cgo is required:
the SQLite driver is the pure-Go `modernc.org/sqlite`.

## Requirements

- Go 1.22 or newer (the router uses method-and-path patterns; the module
  currently targets the Go toolchain in `go.mod`)

## Setup

```sh
git clone <repo-url> bookapi
cd bookapi
go mod download
```

## Run

```sh
go run .
```

The server listens on port `8080` and stores data in `books.db` in the current
directory. Both can be overridden:

| Variable  | Default     | Purpose                              |
|-----------|-------------|--------------------------------------|
| `PORT`    | `8080`      | HTTP listen port                     |
| `DB_PATH` | `books.db`  | Path to the SQLite database file     |

```sh
PORT=9000 DB_PATH=/var/lib/bookapi/books.db go run .
```

To build a binary:

```sh
go build -o bookapi .
./bookapi
```

## Test

```sh
go test ./...
```

Tests use an in-memory SQLite database and `net/http/httptest`, so they need no
running server.

## API

All request and response bodies are JSON. Errors are returned as
`{"error": "<message>"}`. Validation failures return `422` with per-field
detail in `details`.

### Book fields

| Field    | Type    | Required | Notes                                              |
|----------|---------|----------|----------------------------------------------------|
| `id`     | integer | —        | Assigned by the server; read-only                  |
| `title`  | string  | yes      | Non-blank after trimming whitespace                |
| `author` | string  | yes      | Non-blank after trimming whitespace                |
| `year`   | integer | no       | If provided, 1 to next calendar year               |
| `isbn`   | string  | no       | If provided, 10 or 13 characters (digits, hyphens allowed, trailing `X` for ISBN-10). Shape check only. Must be unique among books that have one. |

### Endpoints

| Method   | Path          | Success                | Description                              |
|----------|---------------|------------------------|------------------------------------------|
| `POST`   | `/books`      | `201 Created`          | Create a book. `Location` header set.    |
| `GET`    | `/books`      | `200 OK`               | List books, ordered by id. Supports `?author=` (exact match, case-insensitive). |
| `GET`    | `/books/{id}` | `200 OK`               | Get one book.                            |
| `PUT`    | `/books/{id}` | `200 OK`               | Replace a book's fields (full update).   |
| `DELETE` | `/books/{id}` | `204 No Content`       | Delete a book.                           |
| `GET`    | `/health`     | `200 OK`               | Liveness/DB reachability check.          |

### Status codes

| Code | When                                                            |
|------|-----------------------------------------------------------------|
| 400  | Malformed JSON, unknown fields, non-integer or non-positive id  |
| 404  | No book with that id                                            |
| 405  | Unsupported method on a known path                              |
| 409  | ISBN already used by another book                               |
| 413  | Request body over 1 MiB                                         |
| 422  | Validation failed (missing title/author, bad year or ISBN)      |
| 503  | Health check: database unreachable                              |

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List, filtered by author
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Project layout

| File            | Contents                                              |
|-----------------|-------------------------------------------------------|
| `main.go`       | Entry point; reads env config; graceful shutdown       |
| `handlers.go`   | HTTP routes, request decoding, response encoding       |
| `store.go`      | SQLite schema and data access                          |
| `book.go`       | `Book` model, input normalisation and validation       |
| `*_test.go`     | Unit and HTTP-level tests                              |
