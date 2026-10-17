# Book Collection API

A small REST API for managing a book collection, written in Go with the
standard library `net/http` router and SQLite storage. The SQLite driver is
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go
implementation, so no C compiler or cgo is required.

## Requirements

- Go 1.22 or newer (the code is tested with Go 1.26)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

Flags:

| Flag    | Default     | Description                      |
|---------|-------------|----------------------------------|
| `-addr` | `:8080`     | HTTP listen address              |
| `-db`   | `books.db`  | Path to the SQLite database file |

The database file and schema are created automatically on first start.
The server shuts down gracefully on `Ctrl-C` or `SIGTERM`.

Example:

```sh
go run . -addr :9000 -db ./data/books.db
```

## Test

```sh
go test ./...
```

The tests cover validation rules, the full CRUD lifecycle, the author filter,
malformed input handling, ISBN conflicts, and the health endpoint. Integration
tests run against a real SQLite database in a temporary directory.

## Data model

| Field    | Type    | Required | Rules                                                        |
|----------|---------|----------|--------------------------------------------------------------|
| `id`     | integer | —        | Assigned by the server, read-only                            |
| `title`  | string  | yes      | Non-blank after trimming whitespace                          |
| `author` | string  | yes      | Non-blank after trimming whitespace                          |
| `year`   | integer | no       | `0` means unknown; otherwise must be between 1000 and 9999   |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13 format; hyphens and spaces are removed. Checksum is not verified. Must be unique when present. |

## Endpoints

| Method   | Path          | Description                          | Success |
|----------|---------------|--------------------------------------|---------|
| `POST`   | `/books`      | Create a book                        | `201`   |
| `GET`    | `/books`      | List books (optional `?author=`)     | `200`   |
| `GET`    | `/books/{id}` | Get a book by ID                     | `200`   |
| `PUT`    | `/books/{id}` | Replace a book's fields              | `200`   |
| `DELETE` | `/books/{id}` | Delete a book                        | `204`   |
| `GET`    | `/health`     | Health check (verifies database)     | `200`   |

`PUT` replaces the whole book, so `title` and `author` are required on every
update. Send `"year": 0` or `"isbn": ""` to clear those optional fields.

The `?author=` filter is an exact match that ignores case, so
`?author=frank herbert` matches `Frank Herbert`.

### Examples

Create:

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'
```

```json
{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
```

List by author:

```sh
curl 'localhost:8080/books?author=Frank%20Herbert'
```

Update:

```sh
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":""}'
```

Delete:

```sh
curl -i -X DELETE localhost:8080/books/1
```

Health:

```sh
curl localhost:8080/health
# {"status":"ok"}
```

## Errors

Every error response is JSON of the form `{"error": "..."}`. Validation
failures also include a `fields` object that maps each invalid field to a
message:

```json
{
  "error": "validation failed",
  "fields": {
    "title": "title is required",
    "author": "author is required"
  }
}
```

| Status | Meaning                                                                 |
|--------|-------------------------------------------------------------------------|
| `400`  | Invalid JSON, unknown fields, wrong types, validation failure, bad ID    |
| `404`  | Book not found                                                          |
| `409`  | Another book already has this ISBN                                      |
| `413`  | Request body larger than 1 MiB                                          |
| `500`  | Unexpected server or database error                                     |
| `503`  | Health check failed: database unreachable                               |

Request bodies must be a single JSON object. Unknown fields are rejected.

## Project layout

| File             | Purpose                                              |
|------------------|------------------------------------------------------|
| `main.go`        | Entry point: flags, startup, graceful shutdown       |
| `server.go`      | HTTP routes, handlers, JSON helpers                  |
| `store.go`       | SQLite schema and data access                        |
| `book.go`        | Book model, input normalization and validation       |
| `server_test.go` | Integration tests over HTTP against real SQLite      |
| `book_test.go`   | Unit tests for validation and ISBN normalization     |
