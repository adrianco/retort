# Book Collection API

A small REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite for storage. The SQLite driver
(`modernc.org/sqlite`) is pure Go, so no C compiler or cgo is required.

## Requirements

- Go 1.22 or newer (the router uses method and path-parameter patterns)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current directory.
Both can be changed with environment variables:

| Variable  | Default    | Purpose                          |
|-----------|------------|----------------------------------|
| `ADDR`    | `:8080`    | Address to listen on             |
| `DB_PATH` | `books.db` | Path to the SQLite database file |

Example:

```sh
ADDR=:9000 DB_PATH=/var/lib/books/books.db go run .
```

To build a binary instead:

```sh
go build -o bookapi .
./bookapi
```

## Test

```sh
go test ./...
```

Tests run against an in-memory SQLite database and cover the HTTP endpoints, input
validation, malformed requests, ISBN checksums, and persistence across reopening the database.

## API

All request and response bodies are JSON. Errors have the form `{"error": "..."}`;
validation failures also include `"details"` mapping each invalid field to a message.

### Book resource

| Field    | Type    | Required | Notes                                             |
|----------|---------|----------|---------------------------------------------------|
| `id`     | integer | —        | Assigned by the server; read-only                 |
| `title`  | string  | yes      | Non-blank                                         |
| `author` | string  | yes      | Non-blank                                         |
| `year`   | integer | no       | `0` or omitted means unknown; otherwise 1450 to next year |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13, hyphens and spaces allowed; empty means unknown |

### Endpoints

| Method   | Path          | Success | Description                                 |
|----------|---------------|---------|---------------------------------------------|
| `POST`   | `/books`      | `201`   | Create a book. Returns the book and a `Location` header. |
| `GET`    | `/books`      | `200`   | List all books. Supports `?author=` (case-insensitive exact match). |
| `GET`    | `/books/{id}` | `200`   | Get one book.                               |
| `PUT`    | `/books/{id}` | `200`   | Replace a book's fields. Requires the full set of fields. |
| `DELETE` | `/books/{id}` | `204`   | Delete a book.                              |
| `GET`    | `/health`     | `200`   | Liveness and DB check. `503` if the database is unreachable. |

### Status codes

- `400` — invalid JSON, unknown fields, wrong field types, validation failure, or a non-positive / non-numeric `id`
- `404` — no book with that `id`
- `405` — wrong method for a known path
- `413` — request body larger than 1 MiB
- `500` — unexpected server error

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"0-441-17271-7"}'

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

| File            | Contents                                              |
|-----------------|-------------------------------------------------------|
| `main.go`       | Entry point: configuration, server, graceful shutdown |
| `handlers.go`   | Routing and HTTP handlers                             |
| `store.go`      | SQLite persistence                                    |
| `book.go`       | Book model, input normalization, validation           |
| `server_test.go`| Integration and unit tests                            |
