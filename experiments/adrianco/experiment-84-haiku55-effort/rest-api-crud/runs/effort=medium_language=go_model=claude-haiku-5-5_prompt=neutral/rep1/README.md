# Book Collection API

A small REST API for managing a book collection. Written in Go using only the standard
library HTTP router (Go 1.22+ pattern routing) plus a pure-Go SQLite driver, so no C
toolchain is needed. Data is stored in a single SQLite file.

## Requirements

- Go 1.22 or newer (developed and tested with Go 1.26)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi
```

Flags (each also has an environment variable fallback):

| Flag   | Env       | Default     | Description                    |
|--------|-----------|-------------|--------------------------------|
| `-addr`| `ADDR`    | `:8080`     | HTTP listen address            |
| `-db`  | `DB_PATH` | `books.db`  | Path to the SQLite database    |

Example:

```sh
./bookapi -addr :9000 -db /tmp/books.db
```

## Test

```sh
go test ./...
# with the race detector
go test -race ./...
```

Tests run the full HTTP stack against a real SQLite database in a temporary directory.

## API

All requests and responses use JSON. Errors have the shape `{"error": "..."}`.

### Book fields

| Field    | Type    | Required | Rules                                                            |
|----------|---------|----------|------------------------------------------------------------------|
| `id`     | integer | (server) | Assigned on create; read-only                                    |
| `title`  | string  | yes      | Non-blank after trimming whitespace                              |
| `author` | string  | yes      | Non-blank after trimming whitespace                              |
| `year`   | integer | no       | `0` to next calendar year; defaults to `0` (unknown) if omitted |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13 with valid check digit; hyphens/spaces allowed; must be unique when present |

### Endpoints

| Method   | Path          | Success        | Description                                  |
|----------|---------------|----------------|----------------------------------------------|
| `POST`   | `/books`      | `201 Created`  | Create a book. Sets `Location` header.       |
| `GET`    | `/books`      | `200 OK`       | List books, ordered by id. Supports `?author=` |
| `GET`    | `/books/{id}` | `200 OK`       | Get one book                                 |
| `PUT`    | `/books/{id}` | `200 OK`       | Replace a book's fields (full update)        |
| `DELETE` | `/books/{id}` | `204 No Content` | Delete a book                              |
| `GET`    | `/health`     | `200 OK`       | Liveness/readiness; pings the database. Returns `503` if the database is unreachable. |

`?author=` matches the author case-insensitively and must be an exact match of the full
author name (e.g. `?author=frank herbert`).

`PUT` requires the full set of fields; it is not a partial patch.

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'

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

### Status codes

| Code | When                                                              |
|------|-------------------------------------------------------------------|
| 200  | Successful read or update                                         |
| 201  | Book created                                                      |
| 204  | Book deleted                                                      |
| 400  | Malformed JSON, unknown fields, trailing data, invalid id, or validation failure |
| 404  | Book not found                                                    |
| 405  | Method not allowed for the path (includes an `Allow` header)      |
| 409  | ISBN already used by another book                                 |
| 413  | Request body larger than 1 MiB                                    |
| 500  | Unexpected server/database error (details are logged, not returned) |
| 503  | `/health` when the database is unavailable                        |

Validation failures return the list of offending fields:

```json
{
  "error": "validation failed",
  "fields": {
    "title": "is required",
    "author": "is required"
  }
}
```

## Project layout

| File             | Purpose                                              |
|------------------|------------------------------------------------------|
| `main.go`        | Entry point: flags, server config, graceful shutdown |
| `server.go`      | Routes, HTTP handlers, JSON helpers                  |
| `store.go`       | SQLite persistence                                   |
| `book.go`        | Book model, normalisation, validation, ISBN checks   |
| `*_test.go`      | Unit tests (validation) and HTTP integration tests   |
